#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND ANALİZİ — ölçüm katmanı. Yazının ve figürlerin BÜTÜN sayıları buradan.

Bu bir hat değil, tek bir analizin ölçümü. Analiz yayımlandığı günün metnidir
(karar 08.09.2026); girdi `veri/` altındaki dondurulmuş arşivdir
(`arsiv_veri.py`, bulutta) ve bu modül AĞA ÇIKMAZ. Her dosyanın özü künyedeki
sha256'ya karşı her okumada yeniden sınanır: arşiv sessizce değişirse ölçüm
düşer.

SÖZLEŞMELER (her biri ölçülerek kondu, gerekçesi yanında):

* SPREAD = ülkenin 10 yıllık gösterge getirisi − Almanya 10 yıllık gösterge
  getirisi, AYNI kaynaktan ve AYNI zaman damgasından (CNBC/Tullett Prebon).
  İki bacağı ayrı kaynaktan almak farkın içine iki kaynağın yöntem ve saat
  farkını koyar. Sabit vadeli Fransa serisi (Banque de France TEC10) anahtarsız
  erişilemedi. Kaynak SINANDI: aylık ortalaması ECB'nin resmî Maastricht
  serisiyle (IRS) 315 ayda korelasyon 0,996, ortalama fark −3,5 bp
  (`kaynak_sinamasi`).
* GÜNÜN SAATİ: hafta içi bar PARİS 17:30 kotasyonudur — gün içi dakikalık
  barlarla ölçüldü (keşif #32: Almanya 2y 01.10 gün içi 17:30 = 3,0535 = günlük
  kapanış; Almanya 10y 3,5203 ↔ 3,5191; Fransa 10y 4,9256 ↔ 4,9282) ve ECB AAA
  eğrisiyle aynı gün korelasyonu 0,87–0,90. HAFTA SONU barı ATILIR: 564
  cuma–cumartesi çiftinin 550'sinde cumartesi farklı, yani cuma 17:30'dan
  sonraki kotasyonlar cumartesiye yazılıyor; bir Avrupa seansı değildir.
* TAŞINMIŞ İŞ GÜNÜ: Fransa ve Almanya bacaklarının İKİSİ DE bir önceki iş
  gününün değerini birebir taşıyorsa o gün piyasa kapalıdır (tatil) ve atılır.
  Tek bacağın aynı kalması bir ölçümdür.
* EUR/USD: NEW YORK 17:00 KAPANIŞI (CNBC günlük döviz barı; veri gününün barı
  henüz yazılmadığı için o gün dakikalık arşivin 23:00 Paris kotasyonundan).
  ECB referans kuru (14:15 CET) İLK sürümde ana ölçüydü ve YANLIŞ saatti: ABD
  verileri 14:30 CET'te, yani sabitlemeden SONRA çıkıyor ve CNBC'nin ABD getiri
  barları Paris 17:40–20:00 arası bir anlık görüntü (gün içi barlarla ölçüldü:
  01.10 us2y günlük 4,787, 17:30'da 4,810). Sabitleme kuruyla kurulan haftalık
  modelde ABD verisinin faiz farkına yaptığı şok kura bir hafta sonra giriyor ve
  faiz katsayısı sıfıra doğru eziliyordu (2024–2026 t −1,4 → NY kapanışıyla
  −5,3). ECB kuru yalnız sağlamlık sütunu olarak ölçülür.
* ÇAPRAZ KURLAR (EUR/GBP, EUR/CHF, EUR/JPY): Yahoo. Yahoo'nun TAMAMLANMIŞ günlük
  döviz barı 4 Ağustos 2010'dan beri bir önceki iş gününün New York kapanışını
  taşır, öncesinde aynı günün (CNBC NY kapanışına karşı ölçüldü: kaydırılmış
  seride medyan fark 0,0006; kaydırılmamışta 0,003); son bar canlı kotasyondur
  (1 Ekim 23:06 Paris). Hiza her koşuda yeniden sınanır (`_yahoo_hiza`).
  Kaydırılmamış çapraz, Paris 17:30 getirisini bir gün önceki kurla kıyaslar.
  DXY Yahoo'da aynı gün etiketlidir (korelasyon kaydırmasız −0,90, kaydırmalı
  −0,05). GBP/USD ve CHF/USD bu çaprazlardan türetilir: ln EUR/USD =
  ln GBP/USD + ln EUR/GBP özdeşliği kurun kaybını model kullanmadan bir DOLAR
  bacağına ve bir EURO bacağına ayırır.
* Kur–spread ilişkisi HAFTALIK (çarşamba–çarşamba) ölçülür: getiri Paris 17:30,
  kur New York 17:00 (Paris 23:00); günün ABD verisi ikisinde de var. Çarşamba:
  cuma ve pazartesi tatillerinden en az etkilenen gün.
* Değişimler baz puan (bp); seviyeler yüzde; kur değişimi log-yüzde.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"

# Yazının veri günü: arşivin son kapanmış Avrupa seansı.
SON_GUN = "2026-10-01"
# 2026 epizodunun başlangıcı: yılın dibi (ölçülür, `seviye_ozeti` sınar).
EPIZOT_BAS = "2026-02-25"
ULKE_AD = {"fr": "Fransa", "de": "Almanya", "it": "İtalya", "es": "İspanya", "be": "Belçika",
           "nl": "Hollanda", "at": "Avusturya", "pt": "Portekiz", "gr": "Yunanistan"}


class ArsivHatasi(RuntimeError):
    pass


# ── arşiv ─────────────────────────────────────────────────────────────────
@lru_cache(maxsize=None)
def kunye() -> dict:
    return json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def oku(ad: str) -> pd.DataFrame:
    """Arşiv dosyasını okur; özü künyeyle KARŞILAŞTIRIR."""
    k = kunye()["dosyalar"].get(ad)
    if k is None:
        raise ArsivHatasi(f"{ad} künyede yok")
    ham = gzip.decompress((VERI / ad).read_bytes())
    oz = hashlib.sha256(ham).hexdigest()
    if oz != k["sha256"]:
        raise ArsivHatasi(f"{ad} özü künyeyle tutmuyor: {oz[:12]} ≠ {k['sha256'][:12]}")
    df = pd.read_csv(io.BytesIO(ham), index_col=0, parse_dates=True)
    return df.sort_index()


# ── temiz günlük çerçeve ─────────────────────────────────────────────────
@lru_cache(maxsize=None)
def _gunluk_sayimli() -> tuple[pd.DataFrame, dict]:
    ham = oku("cnbc_gunluk.csv.gz")
    ham = ham[ham.index <= SON_GUN]
    hs = ham.index.dayofweek >= 5
    df = ham[~hs].copy()
    tas = (df["fr10y"].diff() == 0) & (df["de10y"].diff() == 0)
    sayim = {"ham_bar": int(len(ham)), "hafta_sonu_atilan": int(hs.sum()),
             "tasinmis_atilan": int(tas.sum()),
             "tasinmis_son": [str(t.date()) for t in df.index[tas]][-6:]}
    df = df[~tas]
    sayim["temiz_gun"] = int(len(df))
    return df, sayim


def gunluk() -> pd.DataFrame:
    return _gunluk_sayimli()[0]


def temizlik_sayimi() -> dict:
    return dict(_gunluk_sayimli()[1])


YAHOO_KAYMA_BAS = "2010-08-04"


@lru_cache(maxsize=None)
def kur_ny() -> pd.Series:
    """EUR/USD, New York 17:00 kapanışı. Veri gününün barı CNBC'de henüz yok;
    o gün dakikalık arşivin Paris 23:00'e kadarki son kotasyonu kullanılır."""
    s = oku("cnbc_gunluk.csv.gz")["eurusd"].dropna()
    s = s[(s.index.dayofweek < 5) & (s.index <= SON_GUN)].copy()
    if pd.Timestamp(SON_GUN) not in s.index:
        g = gun_ici()["eurusd"].dropna()
        g = g[(g.index.date == pd.Timestamp(SON_GUN).date()) & (g.index.strftime("%H:%M") <= "23:00")]
        if g.empty:
            raise ArsivHatasi("veri gününün New York kapanışı arşivde yok")
        s.loc[pd.Timestamp(SON_GUN)] = float(g.iloc[-1])
    return s.sort_index()


@lru_cache(maxsize=None)
def yahoo_ny(kod: str) -> pd.Series:
    """Yahoo döviz barını New York kapanışı gününe hizalar (bkz. başlık)."""
    s = oku("yahoo_gunluk.csv.gz")[kod].dropna()
    s = s[s.index <= SON_GUN]
    son_t, son_v = s.index[-1], float(s.iloc[-1])
    tam = s.iloc[:-1]
    eski = tam[tam.index < YAHOO_KAYMA_BAS]
    yeni = tam[tam.index >= YAHOO_KAYMA_BAS].copy()
    yeni.index = yeni.index - pd.tseries.offsets.BDay(1)
    out = pd.concat([eski, yeni])
    out = out[~out.index.duplicated(keep="last")]
    out.loc[son_t] = son_v
    return out.sort_index()


def _yahoo_hiza() -> dict:
    """Hizalanmış Yahoo EUR/USD ile CNBC New York kapanışı aynı mı? Kural
    bozulursa (Yahoo etiket sözleşmesini değiştirirse) ölçüm DÜŞER."""
    ny, ya = kur_ny(), yahoo_ny("eurusd")
    out = {}
    for ad, a, b in (("2004–2010", "2004-01-01", "2010-07-30"), ("2010–2026", "2010-08-16", SON_GUN)):
        j = pd.concat([ny.rename("n"), ya.rename("y")], axis=1, sort=True).dropna()
        j = j[(j.index >= a) & (j.index <= b)]
        out[ad] = {"n": int(len(j)), "medyan_fark": float((j["n"] - j["y"]).abs().median())}
        if out[ad]["medyan_fark"] > 0.0015:
            raise ArsivHatasi(f"Yahoo döviz hizası tutmuyor ({ad}): medyan fark {out[ad]['medyan_fark']:.4f}")
    # Kıyas: kaydırılmamış Yahoo barı 2010 sonrasında aynı günün NY kapanışına ne kadar uzak?
    ham = oku("yahoo_gunluk.csv.gz")["eurusd"].dropna()
    j = pd.concat([ny.rename("n"), ham.rename("y")], axis=1, sort=True).dropna()
    j = j[(j.index >= "2010-08-16") & (j.index < SON_GUN)]
    out["kaydirmasiz_2010_2026"] = {"n": int(len(j)), "medyan_fark": float((j["n"] - j["y"]).abs().median())}
    return out


def spread(ulke: str = "fr", vade: int = 10, karsi: str = "de") -> pd.Series:
    """Ülke − karşı ülke gösterge getirisi farkı, baz puan. İki bacak aynı
    gün ölçülmemişse fark kurulmaz."""
    df = gunluk()
    return ((df[f"{ulke}{vade}y"] - df[f"{karsi}{vade}y"]) * 100).dropna()


def _once(s: pd.Series, gun: str) -> tuple[str, float]:
    """`gun` ya da ondan önceki son gözlem."""
    s = s[s.index <= gun].dropna()
    return str(s.index[-1].date()), float(s.iloc[-1])


def _son_gorulme(s: pd.Series) -> str | None:
    """Bugünkü seviyeye ya da üstüne en son ne zaman çıkıldı (bugünden önce)."""
    once = s[s.index < s.index[-1]]
    ust = once[once >= s.iloc[-1]]
    return str(ust.index[-1].date()) if len(ust) else None


# ── 1. seviye ve konum ────────────────────────────────────────────────────
def seviye_ozeti() -> dict:
    s = spread()
    df = gunluk()
    son = float(s.iloc[-1])
    out = {"gun": str(s.index[-1].date()), "spread": son,
           "fr10": float(df["fr10y"].dropna().iloc[-1]),
           "de10": float(df["de10y"].dropna().iloc[-1])}
    # n iş günü önceki gözlem: iloc[-(n+1)] (1 ay = 22 iş günü, hız ölçüsüyle aynı).
    for ad, i in (("1g", -2), ("1h", -6), ("1a", -23)):
        out[f"degisim_{ad}"] = son - float(s.iloc[i])
        out[f"tarih_{ad}"] = str(s.index[i].date())
    for ad, gun in (("yb", "2025-12-31"), ("haziran", "2026-06-30"), ("agustos", "2026-08-31")):
        t, v = _once(s, gun)
        out[f"seviye_{ad}"], out[f"tarih_{ad}"], out[f"degisim_{ad}"] = v, t, son - v
    out["son_gorulme"] = _son_gorulme(s)
    us = df["us10y"].dropna()
    out["us10_son"], out["us10_onceki"] = float(us.iloc[-1]), float(us.iloc[-2])
    out["us10_onceki_gun"] = str(us.index[-2].date())
    # 100 bp eşiği: 2026'da ilk aşıldığı gün ve ondan önce en son aşıldığı gün.
    y100 = s[(s.index >= "2026-01-01") & (s >= 100)]
    out["ilk_100"] = str(y100.index[0].date())
    out["onceki_100"] = str(s[(s >= 100) & (s.index < y100.index[0])].index[-1].date())
    out["yuzdelik_2000"] = float((s < son).mean() * 100)
    out["tarihi_zirve"], out["tarihi_zirve_gun"] = float(s.max()), str(s.idxmax().date())
    yil = s[s.index >= "2026-01-01"]
    out["yil_dibi"], out["yil_dibi_gun"] = float(yil.min()), str(yil.idxmin().date())
    out["epizot_degisim"] = son - out["yil_dibi"]
    # Yılın dibi epizodun tanımıdır; sabit yazılan EPIZOT_BAS ölçüyle tutmalı.
    out["epizot_bas_tutarli"] = out["yil_dibi_gun"] == EPIZOT_BAS
    # Bacakların payı: Haziran sonundan bu yana spread artışının ne kadarı OAT'tan.
    t0 = out["tarih_haziran"]
    a, b = df.loc[:t0].dropna(subset=["fr10y", "de10y"]).iloc[-1], df.dropna(subset=["fr10y", "de10y"]).iloc[-1]
    out["haziran_fr_bp"] = float((b["fr10y"] - a["fr10y"]) * 100)
    out["haziran_de_bp"] = float((b["de10y"] - a["de10y"]) * 100)
    # Eylül günleri: en büyük tek günlük açılmalar
    eyl = s[s.index > "2026-08-31"].diff().dropna()
    out["eylul_en_buyuk"] = [(str(t.date()), float(v)) for t, v in eyl.sort_values(ascending=False).head(5).items()]
    out["gunluk_seri_son"] = [(str(t.date()), float(v)) for t, v in s[s.index > "2026-08-27"].items()]
    return out


def kaynak_sinamasi() -> dict:
    """CNBC'den kurulan aylık ortalama farklar ECB'nin resmî serisine karşı."""
    irs = oku("irs_aylik.csv.gz")
    out = {}
    for u in ("fr", "it", "es", "be"):
        cn = spread(u).resample("ME").mean()
        resmi = (irs[u.upper()] - irs["DE"]) * 100
        j = pd.concat([cn.rename("c"), resmi.rename("r")], axis=1, sort=True).dropna()
        f = j["c"] - j["r"]
        out[u] = {"ay": int(len(j)), "korelasyon": float(j.corr().iloc[0, 1]),
                  "degisim_korelasyonu": float(j.diff().dropna().corr().iloc[0, 1]),
                  "yillik_fark_min": float(f.groupby(f.index.year).mean().min()),
                  "yillik_fark_maks": float(f.groupby(f.index.year).mean().max()),
                  "ort_fark": float(f.mean()), "mutlak_medyan": float(f.abs().median()),
                  "son_ay": str(j.index[-1].date()), "son_ay_resmi": float(j["r"].iloc[-1]),
                  "son_ay_cnbc": float(j["c"].iloc[-1])}
    return out


# ── 2. akranlar ───────────────────────────────────────────────────────────
AKRAN = ("fr", "it", "gr", "be", "es", "pt", "at", "nl")


def akranlar() -> list[dict]:
    out = []
    for u in AKRAN:
        s = spread(u)
        t_h, v_h = _once(s, "2026-06-30")
        out.append({"ulke": u, "ad": ULKE_AD[u], "gun": str(s.index[-1].date()), "spread": float(s.iloc[-1]),
                    "haziran": v_h, "degisim_haziran": float(s.iloc[-1]) - v_h,
                    "getiri": float(gunluk()[f"{u}10y"].dropna().iloc[-1])})
    return sorted(out, key=lambda r: -r["spread"])


def fransa_italya() -> dict:
    """Fransa'nın 10 yıllığı İtalya'nınkinin üstünde mi, ne zamandan beri."""
    f = spread("fr", 10, "it")
    son_neg = f[f <= 0].index[-1]
    sonra = f[f.index > son_neg]
    fe = spread("fr", 10, "es")
    son_neg_es = fe[fe <= 0].index[-1]
    return {"fr_eksi_it": float(f.iloc[-1]), "kesintisiz_bas": str(sonra.index[0].date()) if len(sonra) else None,
            "gun_sayisi": int(len(sonra)),
            "is_gunu": int(len(pd.bdate_range(sonra.index[0], sonra.index[-1]))) if len(sonra) else 0,
            "eksik_gunler": [str(d.date()) for d in pd.bdate_range(sonra.index[0], sonra.index[-1]).difference(sonra.index)] if len(sonra) else [],
            "tarihce_zirve": float(f.max()), "tarihce_zirve_gun": str(f.idxmax().date()),
            "2000_sonrasi_pozitif_gun": int((f > 0).sum()), "toplam_gun": int(len(f)),
            "ilk_pozitif": str(f[f > 0].index[0].date()) if (f > 0).any() else None,
            "fr_eksi_es": float(fe.iloc[-1]), "es_kesintisiz_bas": str(fe[fe.index > son_neg_es].index[0].date())}


# ── 3. eğri ───────────────────────────────────────────────────────────────
def egri() -> dict:
    out = {}
    for v in (2, 5, 10, 30):
        s = spread("fr", v)
        out[v] = {"spread": float(s.iloc[-1]), "gun": str(s.index[-1].date()),
                  "degisim_1g": float(s.iloc[-1] - s.iloc[-2]),
                  "degisim_haziran": float(s.iloc[-1]) - _once(s, "2026-06-30")[1],
                  "son_gorulme": _son_gorulme(s), "zirve": float(s.max()), "zirve_gun": str(s.idxmax().date()),
                  "en_buyuk_tek_gun_once": None}
        d = s.diff().dropna()
        ust = d[(d.index < d.index[-1]) & (d >= d.iloc[-1])]
        out[v]["tek_gun_son_gorulme"] = str(ust.index[-1].date()) if len(ust) else None
    i2 = spread("it", 2)
    out["it2"] = {"spread": float(i2.iloc[-1]), "degisim_1g": float(i2.iloc[-1] - i2.iloc[-2])}
    i10 = spread("it", 10)
    out["it10"] = {"spread": float(i10.iloc[-1]), "degisim_1g": float(i10.iloc[-1] - i10.iloc[-2])}
    df = gunluk()
    for k in ("de2y", "fr2y", "de5y", "fr5y", "de10y", "fr10y", "de30y", "fr30y", "us2y", "it2y", "it10y"):
        s = df[k].dropna()
        out[f"{k}_1g_bp"] = float((s.iloc[-1] - s.iloc[-2]) * 100)
    # Fark sıçramasının bacakları: Almanya bacağının payı (Fransa ve İtalya).
    for v in (2, 5, 10, 30):
        out[v]["de_payi"] = -out[f"de{v}y_1g_bp"] / out[v]["degisim_1g"]
    out["it2"]["de_payi"] = -out["de2y_1g_bp"] / out["it2"]["degisim_1g"]
    # Son beş iş günü (24.09 → veri günü) 2 yıllıkta.
    s2, a2 = spread("fr", 2), df["de2y"].dropna()
    f2 = df["fr2y"].dropna()
    out["bes_gun_2y"] = {"bas": str(s2.index[-6].date()), "spread_bas": float(s2.iloc[-6]),
                         "spread_son": float(s2.iloc[-1]), "de_bp": float((a2.iloc[-1] - a2.iloc[-6]) * 100),
                         "fr_bp": float((f2.iloc[-1] - f2.iloc[-6]) * 100)}
    return out


# ── 4. epizotlar ──────────────────────────────────────────────────────────
# Başlangıç günü olayın son iş günüdür; iki istisna adıyla yazılır: 2011'de
# belirli bir olay yok (yaz bulaşma dalgasından önceki ölçü günü), 2026'da
# başlangıç yılın dibidir (sonradan seçildi, açılmayı büyütür). Bitiş, zirvenin
# arandığı sınırdır ve tabloya yazılır. 2017: 9 Kasım 2016'dan başlatmak ABD
# seçiminin ertesindeki küresel satışı (32,6 → 60,1 bp, 28.11.2016) Fransa
# siyasetine yazıyordu; başlangıç Fillon soruşturmasının açıldığı haftaya
# alındı (Le Canard enchaîné, 25.01.2017). Bayrou: pencere Lecornu
# istifasından önce kesilir (06.10.2025 ayrı bir olaydır, olay tablosunda).
EPIZOTLAR = [
    ("2008 küresel finans krizi", "2008-09-12", "2009-03-31", "Lehman Brothers'ın çöküşü (15.09.2008)"),
    ("2010 Yunanistan", "2010-04-22", "2010-06-30", "Yunanistan açık revizyonu, ilk kurtarma paketi"),
    ("2011 euro bölgesi borç krizi", "2011-07-01", "2011-12-31", "İtalya ve İspanya'ya bulaşma; olay günü değil, ölçü günü"),
    ("2017 cumhurbaşkanlığı seçimi", "2017-01-24", "2017-04-21", "Fillon soruşturmasının açılması (25.01.2017)"),
    ("2020 salgın", "2020-02-21", "2020-04-30", "salgın şoku"),
    ("2024 meclisin feshi", "2024-06-07", "2024-07-31", "9 Haziran 2024 fesih kararı (son iş günü 7 Haziran)"),
    ("2024 Barnier hükümetinin düşüşü", "2024-11-29", "2024-12-31", "4 Aralık 2024 gensoru"),
    ("2025 Bayrou güven oylaması", "2025-08-22", "2025-10-03", "25 Ağustos 2025 güven oylaması duyurusu"),
    ("2026", EPIZOT_BAS, SON_GUN, "yılın dibi (sonradan seçildi)"),
]


def _isgunu(a: str, b: str) -> int:
    return int(np.busday_count(pd.Timestamp(a).date(), pd.Timestamp(b).date()))


def epizotlar() -> list[dict]:
    s, it = spread("fr"), spread("it")
    fx = kur_ny()
    gb = yahoo_ny("eurgbp")
    df = gunluk()
    rd = ((df["us2y"] - df["de2y"]) * 100).dropna()
    out = []
    for ad, a, b, olay in EPIZOTLAR:
        p = s[(s.index >= a) & (s.index <= b)]
        tz = p.idxmax()
        t0, v0 = _once(s, a)
        z = float(p.max())
        r = {"ad": ad, "olay": olay, "bas": t0, "bas_seviye": v0, "zirve": z, "zirve_gun": str(tz.date()),
             "arama_son": b, "acilma": z - v0, "is_gunu": _isgunu(t0, str(tz.date())),
             "eurusd_yuzde": float(100 * (np.log(_once(fx, str(tz.date()))[1]) - np.log(_once(fx, t0)[1]))),
             "eurgbp_yuzde": _tam_degisim(gb, t0, str(tz.date())),
             "rd_bp": _once(rd, str(tz.date()))[1] - _once(rd, t0)[1],
             "it_bp": _once(it, str(tz.date()))[1] - _once(it, t0)[1]}
        for m in (1, 3, 6):
            t = tz + pd.DateOffset(months=m)
            r[f"sonra_{m}a"] = (_once(s, str(t.date()))[1] - z) if t <= s.index[-1] else None
        out.append(r)
    return out


# ── 5. EUR/USD duyarlılığı ────────────────────────────────────────────────
@lru_cache(maxsize=None)
def _gunluk_kur() -> pd.DataFrame:
    """Günlük çerçeve: farklar (Paris 17:30), faiz farkı, New York kapanışlı
    EUR/USD, ECB kuru, hizalanmış çaprazlar. GBP/USD ve CHF/USD özdeşlikten
    (EUR/USD ÷ çapraz) kurulur: dolar bacağı + euro bacağı = EUR/USD, birebir."""
    _yahoo_hiza()
    df = gunluk()
    t = pd.DataFrame({"spr": (df["fr10y"] - df["de10y"]) * 100, "ispr": (df["it10y"] - df["de10y"]) * 100,
                      "rd": (df["us2y"] - df["de2y"]) * 100, "de2": df["de2y"] * 100,
                      "de10": df["de10y"] * 100, "us2": df["us2y"] * 100})
    # Sağlamlık: ABD bacağı ABD Hazinesi'nin resmî getirisi (CNBC'nin ABD barı
    # daha geç ve belirsiz saatli bir anlık görüntü).
    t["rdT"] = (oku("abd_gunluk.csv.gz")["us2"].reindex(t.index) - df["de2y"]) * 100
    t = t.join(kur_ny().rename("fx"), how="left")
    t = t.join(oku("eurusd_ecb.csv.gz")["eurusd_ecb"].rename("fx_ecb"), how="left")
    for k in ("eurgbp", "eurchf", "eurjpy"):
        t = t.join(yahoo_ny(k).rename(k), how="left")
    t["gbpusd"] = t["fx"] / t["eurgbp"]
    t["chfusd"] = t["fx"] / t["eurchf"]
    y = oku("yahoo_gunluk.csv.gz")
    t = t.join(y["vix"].rename("vix"), how="left").join(y["dxy"].rename("dxy"), how="left")
    return t


KUR_KOLON = ("fx", "fx_ecb", "gbpusd", "chfusd", "eurgbp", "eurchf")


@lru_cache(maxsize=None)
def haftalik() -> pd.DataFrame:
    """Çarşamba–çarşamba haftalık değişimler. Kurlar 100·Δln (New York
    kapanışı; fx_ecb: ECB 14:15); rd: Δ(ABD 2y − Almanya 2y), bp; spr: ΔOAT–Bund
    10y, bp; ispr: ΔBTP–Bund 10y. Haftanın son gözlemi BÜTÜN kur ve faiz
    kolonlarının ölçüldüğü son gündür: tek kolonun son değerini ayrı ayrı almak
    farklı günleri aynı haftaya yazar (30.09.2026'da Yahoo barı yok)."""
    t = _gunluk_kur().dropna(subset=["spr", "ispr", "rd"] + list(KUR_KOLON))
    w = t.resample("W-WED").last()
    # Yarım son hafta atılır: kova çarşambada kapanmamışsa (veri günü perşembe)
    # o "hafta" bir günlük değişimdir ve haftalık örnekleme girmez.
    if t.index[-1] < w.index[-1]:
        w = w.iloc[:-1]
    d = pd.DataFrame({k: w[k].diff() for k in ("spr", "ispr", "rd", "rdT", "de2", "de10", "us2")})
    for k in KUR_KOLON + ("eurjpy", "vix"):
        d[k] = np.log(w[k]).diff() * 100
    return d[d.index >= "2004-01-01"].dropna(subset=["fx", "spr", "ispr", "rd"])


def ols(d: pd.DataFrame, y: str, xs: list[str], nw: int = 4) -> dict:
    """En küçük kareler + Newey–West (Bartlett, `nw` gecikme) standart hata."""
    d = d.dropna(subset=[y] + xs)
    X = np.column_stack([np.ones(len(d))] + [d[x].values for x in xs])
    Y = d[y].values
    b, *_ = np.linalg.lstsq(X, Y, rcond=None)
    e = Y - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, nw + 1):
        G = u[L:].T @ u[:-L]
        S += (1 - L / (nw + 1)) * (G + G.T)
    se = np.sqrt(np.diag(XtXi @ S @ XtXi))
    return {"n": int(len(d)), "r2": float(1 - e.var() / Y.var()),
            "b": {x: float(b[i + 1]) for i, x in enumerate(xs)},
            "t": {x: float(b[i + 1] / se[i + 1]) for i, x in enumerate(xs)},
            "sabit": float(b[0]), "bas": str(d.index[0].date()), "son": str(d.index[-1].date())}


DONEMLER = [("2004–2026", "2004-01-01", "2026-12-31"), ("2004–2009", "2004-01-01", "2009-12-31"),
            ("2010–2012", "2010-01-01", "2012-12-31"), ("2013–2019", "2013-01-01", "2019-12-31"),
            ("2020–2023", "2020-01-01", "2023-12-31"), ("2024–2026", "2024-01-01", "2026-12-31")]
# (anahtar, bağımlı değişken, açıklayıcılar). İlk dördü EUR/USD (NY kapanışı);
# "ecb" aynı modelin ECB 14:15 kuruyla sağlamlık sürümü; son beşi YANLIŞLAMA
# sınaması: aynı model sterlinde (GBP/USD — Fransa farkının euroya özgü
# olmayan, dolar geneline giden payı) ve euronun öbür Avrupa paralarına karşı
# kurlarında (EUR/GBP, EUR/CHF — dolar bacağı düşmüş, kalan euroya özgüdür).
MODELLER = [("faiz", "fx", ["rd"]), ("faiz+fr", "fx", ["rd", "spr"]), ("faiz+fr+it", "fx", ["rd", "spr", "ispr"]),
            ("faiz+fr+vix", "fx", ["rd", "spr", "vix"]), ("ecb", "fx_ecb", ["rd", "spr"]),
            ("ecb_faiz", "fx_ecb", ["rd"]), ("hazine+fr", "fx", ["rdT", "spr"]),
            ("gbpusd", "gbpusd", ["rd", "spr"]), ("eurgbp", "eurgbp", ["rd", "spr"]), ("eurchf", "eurchf", ["rd", "spr"]),
            ("eurgbp_it", "eurgbp", ["rd", "spr", "ispr"]), ("eurchf_it", "eurchf", ["rd", "spr", "ispr"])]


def duyarlilik() -> dict:
    d = haftalik()
    out = {}
    for ad, a, b in DONEMLER:
        dd = d[(d.index >= a) & (d.index <= b)]
        out[ad] = {m: ols(dd, y, xs) for m, y, xs in MODELLER}
    return out


def kanallar() -> dict:
    """Spread açıldığında Bund ve EUR/CHF ne yapıyor — haftalık, 2024–2026."""
    d = haftalik()
    dd = d[d.index >= "2024-01-01"]
    return {"de2": ols(dd, "de2", ["spr"]), "de10": ols(dd, "de10", ["spr"]),
            "eurchf": ols(dd, "eurchf", ["spr"]), "vix_spr": ols(dd, "spr", ["vix"])}


def orneklem_disi(kesim: str = "2023-12-31", egitim_bas: str = "2004-01-01", y: str = "fx") -> dict:
    """Katsayılar kesim öncesinde tahmin edilir, sonrasında haftalık kur
    değişimini açıklama gücü ölçülür. Kıyas: yalnız faiz farkı modeli ve sıfır.
    Örneklem dışı R² ortalamaya göre ölçülür: eksi değer, test döneminin kendi
    ortalamasından KÖTÜ tahmin demektir."""
    d = haftalik()
    eg = d[(d.index > egitim_bas) & (d.index <= kesim)]
    te = d[d.index > kesim]
    out = {"egitim": f"{eg.index[0].date()}–{eg.index[-1].date()}", "test": f"{te.index[0].date()}–{te.index[-1].date()}",
           "test_n": int(len(te)), "y": y}
    hata = {}
    for m, xs in (("sifir", []), ("faiz", ["rd"]), ("faiz+fr", ["rd", "spr"]), ("faiz+fr+it", ["rd", "spr", "ispr"])):
        if xs:
            o = ols(eg, y, xs)
            tah = o["sabit"] + sum(o["b"][x] * te[x] for x in xs)
        else:
            tah = pd.Series(0.0, index=te.index)
        e = te[y] - tah
        hata[m] = e
        out[m] = {"r2_dis": float(1 - (e ** 2).sum() / ((te[y] - te[y].mean()) ** 2).sum()),
                  "mae": float(e.abs().mean())}
    # Eşli fark: faiz+fr modeli, faiz modeline göre her hafta kare hatayı azaltıyor mu?
    fark = hata["faiz"] ** 2 - hata["faiz+fr"] ** 2
    out["esli_t"] = float(fark.mean() / (fark.std(ddof=1) / np.sqrt(len(fark))))
    out["kazandigi_hafta_payi"] = float((fark > 0).mean() * 100)
    return out


ATIF_BAS = "2026-08-31"
ATIF_KATSAYI = (("2024-01-01", "2026-06-30"), ("2004-01-01", "2023-12-31"), ("2013-01-01", "2023-12-31"),
                ("2010-01-01", "2012-12-31"), ("2004-01-01", "2026-06-30"))


def epizot_atfi(bas: str = ATIF_BAS, son: str = SON_GUN, kesim: str = "2026-06-30",
                egitim_bas: str = "2024-01-01", y: str = "fx") -> dict:
    """Bir pencerede kurun hareketi: ölçülen ve modelin iki kanala atfettiği.

    Katsayılar pencereden ÖNCE biten bir dönemde (egitim_bas–kesim) haftalık
    örnekte tahmin edilir. Atıf SEVİYELERDEN kurulur (başlangıç günü → bitiş
    günü), saatler tutarlıdır: fark ve faiz farkı Paris 17:30 (ABD bacağı daha
    geç bir anlık görüntü), kur New York 17:00 — kur, iki açıklayıcının o günkü
    hareketinin TAMAMINI görmüştür. Sabit terim haftalık; hafta sayısıyla
    ölçeklenir ve ayrı yazılır, kanallar + sabit + kalan = ölçülen."""
    if pd.Timestamp(kesim) >= pd.Timestamp(bas):
        raise ArsivHatasi(f"atıf penceresi ({bas}) tahmin döneminin ({kesim}) içinde: örneklem içi")
    d = haftalik()
    o = ols(d[(d.index >= egitim_bas) & (d.index <= kesim)], y, ["rd", "spr"])
    t = _gunluk_kur()
    lv = t[y].dropna()
    rd, s = t["rd"].dropna(), t["spr"].dropna()
    hafta = _isgunu(bas, son) / 5
    kur = float(100 * (np.log(_once(lv, son)[1]) - np.log(_once(lv, bas)[1])))
    drd = _once(rd, son)[1] - _once(rd, bas)[1]
    dsp = _once(s, son)[1] - _once(s, bas)[1]
    r = {"y": y, "bas": _once(s, bas)[0], "son": _once(s, son)[0], "kur_bas_gun": _once(lv, bas)[0],
         "kur_son_gun": _once(lv, son)[0], "hafta": hafta, "kur_gercek": kur,
         "faiz_payi": o["b"]["rd"] * drd, "spread_payi": o["b"]["spr"] * dsp,
         "sabit_payi": o["sabit"] * hafta, "rd_toplam": drd, "spr_toplam": dsp, "katsayi": o}
    r["artik"] = kur - (r["faiz_payi"] + r["spread_payi"] + r["sabit_payi"])
    return r


def atif_duyarlilik(bas: str = ATIF_BAS, son: str = SON_GUN, y: str = "fx") -> list[dict]:
    """Kanal atfı, katsayıların tahmin edildiği pencereye ne kadar bağlı?"""
    out = []
    for eg_bas, kesim in ATIF_KATSAYI:
        a = epizot_atfi(bas=bas, son=son, kesim=kesim, egitim_bas=eg_bas, y=y)
        out.append({"egitim": f"{a['katsayi']['bas']}–{a['katsayi']['son']}", "n": a["katsayi"]["n"],
                    "b_spr": a["katsayi"]["b"]["spr"], "b_rd": a["katsayi"]["b"]["rd"],
                    "t_spr": a["katsayi"]["t"]["spr"], "t_rd": a["katsayi"]["t"]["rd"],
                    "spread_payi": a["spread_payi"], "faiz_payi": a["faiz_payi"], "sabit_payi": a["sabit_payi"],
                    "artik": a["artik"], "kur_gercek": a["kur_gercek"]})
    return out


# Model kullanmadan ayrıştırma: ln EUR/USD = ln GBP/USD + ln EUR/GBP.
# Euro bacağı = Δln EUR/GBP (ya da EUR/CHF): dolar her iki parada ortaktır,
# düşer. Dolar bacağı = Δln EUR/USD − euro bacağı. Pencereler: yılın dibi,
# yaz, eylülün iki evresi, eylülün tamamı.
CAPRAZ_PENCERE = (("2026-02-25", SON_GUN), ("2026-06-30", "2026-08-31"), ("2026-08-31", "2026-09-28"),
                  ("2026-09-28", SON_GUN), ("2026-08-31", SON_GUN), ("2026-09-29", SON_GUN))


def capraz_ayrisma() -> list[dict]:
    t = _gunluk_kur()
    out = []
    for a, b in CAPRAZ_PENCERE:
        def L(k):
            v = _tam_degisim(t[k].dropna(), a, b)
            if v is None:
                raise ArsivHatasi(f"çapraz ayrıştırma: {k} {a}→{b} ucu veride yok ya da bayat")
            return v
        def D(k):
            s = t[k].dropna()
            return _once(s, b)[1] - _once(s, a)[1]
        r = {"bas": a, "son": b, "fx": L("fx"), "eurgbp": L("eurgbp"), "eurchf": L("eurchf"),
             "eurjpy": L("eurjpy"), "dxy": L("dxy"), "fx_ecb": L("fx_ecb"),
             "spr": D("spr"), "ispr": D("ispr"), "rd": D("rd"), "us2": D("us2"), "de2": D("de2")}
        r["dolar_gbp"] = r["fx"] - r["eurgbp"]
        r["dolar_chf"] = r["fx"] - r["eurchf"]
        r["euro_payi_gbp"] = r["eurgbp"] / r["fx"] if r["fx"] else None
        r["euro_payi_chf"] = r["eurchf"] / r["fx"] if r["fx"] else None
        out.append(r)
    return out


EVRE = (("2026-08-31", "2026-09-28"), ("2026-09-28", SON_GUN))
EVRE_ULKE = ("fr", "it", "be", "es", "at", "nl", "pt", "gr")


def evreler() -> list[dict]:
    """Eylülün iki evresinde her ülkenin Bund'a farkı, Bund ve ABD eğrisinin
    bacakları. Fransa'ya ÖZGÜ olan, akranlarından ayrıştığı kısımdır
    (Fransa–İtalya); bütün farklar birlikte açılıyorsa hareket euro bölgesi
    genelinedir."""
    df = gunluk()
    out = []
    for a, b in EVRE:
        r = {"bas": a, "son": b}
        for u in EVRE_ULKE:
            s = spread(u)
            ta, va = _once(s, a)
            tb, vb = _once(s, b)
            r[u] = vb - va
            r[f"{u}_gun"] = f"{ta}→{tb}"
        r["fr_eksi_it"] = r["fr"] - r["it"]
        for k in ("de2y", "de10y", "fr10y", "us2y", "us10y", "it10y"):
            s = df[k].dropna()
            r[f"{k}_bp"] = (_once(s, b)[1] - _once(s, a)[1]) * 100
        out.append(r)
    return out


BACAK_PENCERE = ("2026-02-25", "2026-06-30", "2026-08-31", "2026-09-28")


def bacaklar() -> list[dict]:
    """Farkın açılması hangi bacaktan: OAT mı yükseldi, Bund mu düştü? Aynı
    pencerede ABD 10 yıllığı ve İtalya farkı küresel ve bölgesel kıyas."""
    df = gunluk()
    out = []
    for bas in BACAK_PENCERE:
        a = df.loc[:bas].dropna(subset=["fr10y", "de10y"]).iloc[-1]
        b = df.dropna(subset=["fr10y", "de10y"]).iloc[-1]
        us = df["us10y"].dropna()
        out.append({"bas": str(df.loc[:bas].dropna(subset=["fr10y", "de10y"]).index[-1].date()),
                    "fr_bp": float((b["fr10y"] - a["fr10y"]) * 100), "de_bp": float((b["de10y"] - a["de10y"]) * 100),
                    "spr_bp": float(((b["fr10y"] - b["de10y"]) - (a["fr10y"] - a["de10y"])) * 100),
                    "it_spr_bp": float(((b["it10y"] - b["de10y"]) - (a["it10y"] - a["de10y"])) * 100),
                    "us10_bp": float((us.iloc[-1] - _once(us, bas)[1]) * 100)})
    return out


BUYUK_GUNLER = ("2026-09-10", "2026-09-18", "2026-09-21", "2026-09-23", "2026-09-29", "2026-09-30", "2026-10-01")


def buyuk_gunler() -> list[dict]:
    """Eylül'ün büyük günleri: farkın ve bacaklarının günlük değişimi, aynı gün
    ABD 10 yıllığı, İtalya farkı, faiz farkı ve kur. Kur New York kapanışı
    (Paris 23:00), yani getiri barının (17:30) gördüğü hareketin tamamını görür."""
    df = gunluk()
    fx = kur_ny()
    out = []
    for g in BUYUK_GUNLER:
        i = df.index.get_loc(pd.Timestamp(g))
        a, b = df.iloc[i - 1], df.iloc[i]
        fi = fx.index.get_loc(pd.Timestamp(g))
        out.append({"gun": g, "onceki": str(df.index[i - 1].date()),
                    "spr": float(((b["fr10y"] - b["de10y"]) - (a["fr10y"] - a["de10y"])) * 100),
                    "spr_seviye": float((b["fr10y"] - b["de10y"]) * 100),
                    "fr": float((b["fr10y"] - a["fr10y"]) * 100), "de": float((b["de10y"] - a["de10y"]) * 100),
                    "us10": float((b["us10y"] - a["us10y"]) * 100),
                    "it_spr": float(((b["it10y"] - b["de10y"]) - (a["it10y"] - a["de10y"])) * 100),
                    "rd": float(((b["us2y"] - b["de2y"]) - (a["us2y"] - a["de2y"])) * 100),
                    "fx": float(100 * (np.log(fx.iloc[fi]) - np.log(fx.iloc[fi - 1])))})
    return out


# (tür, ad, önceki kapanış, ilk tepki kapanışı). Akşam/hafta sonu açıklanan
# kararlar için önceki = açıklama günü, tepki = ilk işlem günü. Olay günleri
# kaynakla doğrulanmış ya da kayıtlı tarihtir; değişim veriden ölçülür.
OLAY_TEPKI = [
    ("not", "S&P: Fransa AAA → AA+", "2012-01-13", "2012-01-16"),
    ("not", "S&P: AA → AA−", "2024-05-31", "2024-06-03"),
    ("not", "Moody's: Aa2 → Aa3", "2024-12-13", "2024-12-16"),
    ("not", "Fitch: AA− → A+", "2025-09-12", "2025-09-15"),
    ("not", "S&P: AA− → A+", "2025-10-17", "2025-10-20"),
    ("not", "Moody's: görünüm negatife", "2025-10-24", "2025-10-27"),
    ("not", "Moody's: Aa3 teyit, görünüm negatif", "2026-04-10", "2026-04-13"),
    ("not", "S&P: A+ teyit", "2026-05-29", "2026-06-01"),
    ("not", "Fitch: A+ teyit", "2026-08-28", "2026-08-31"),
    ("not", "Scope: AA− → A+; DBRS: eğilim negatife", "2026-09-18", "2026-09-21"),
    ("ecb", "ECB: üç yıllık LTRO", "2011-12-07", "2011-12-08"),
    ("ecb", "Draghi: \"ne gerekiyorsa\"", "2012-07-25", "2012-07-26"),
    ("ecb", "ECB: OMT'nin ayrıntıları", "2012-09-05", "2012-09-06"),
    ("siyaset", "2017 ilk tur: Macron–Le Pen", "2017-04-21", "2017-04-24"),
    ("siyaset", "2024: meclisin feshi", "2024-06-07", "2024-06-10"),
    ("siyaset", "2024: Barnier gensoruyla düştü", "2024-12-04", "2024-12-05"),
    ("siyaset", "2025: Bayrou hükümeti düştü", "2025-09-08", "2025-09-09"),
    ("siyaset", "2025: Lecornu istifa etti", "2025-10-03", "2025-10-06"),
    ("siyaset", "2026: Le Pen istinaf kararı", "2026-07-06", "2026-07-07"),
    ("siyaset", "2026: 54 mlr € çaba açıklandı", "2026-09-16", "2026-09-17"),
    ("siyaset", "2026: 2027 bütçe tasarısı", "2026-09-30", "2026-10-01"),
]


def ayrisma_ornekleri() -> dict:
    """Farkla kurun ayrıştığı iki dönem ve fesih priminin kalıcılığı."""
    s = spread()
    fx = kur_ny()
    a, b = "2025-01-31", "2025-06-30"
    sonra = s[s.index > "2024-06-07"]
    return {"y2025": {"bas": a, "son": b, "fx": float(100 * (np.log(_once(fx, b)[1]) - np.log(_once(fx, a)[1]))),
                      "spr_bas": _once(s, a)[1], "spr_son": _once(s, b)[1]},
            "fesih_once": _once(s, "2024-06-07")[1], "fesih_sonrasi_dip": float(sonra.min()),
            "fesih_sonrasi_dip_gun": str(sonra.idxmin().date())}


def olay_tepkileri() -> list[dict]:
    """Olay günlerinde fark, İtalya farkı, EUR/USD ve EUR/GBP (ikisi de New
    York kapanışı: ECB'nin 14:30 CET basın toplantıları ve öğleden sonraki
    hareket kurun içinde). EUR/GBP sütunu euroya özgü tepkidir."""
    s, it = spread("fr"), spread("it")
    fx, gb = kur_ny(), yahoo_ny("eurgbp")
    out = []
    for tur, ad, a, b in OLAY_TEPKI:
        ta, va = _once(s, a)
        tb, vb = _once(s, b)
        if tb != b or ta != a:
            raise ArsivHatasi(f"olay günü veride yok: {ad} {a}→{b} ({ta}→{tb})")
        out.append({"tur": tur, "ad": ad, "once": a, "sonra": b, "spr_once": va, "spr": vb - va,
                    "it": _once(it, b)[1] - _once(it, a)[1],
                    "fx": float(100 * (np.log(_once(fx, b)[1]) - np.log(_once(fx, a)[1]))),
                    "eurgbp": _tam_degisim(gb, a, b)})
    return out


def _tam_degisim(s: pd.Series, a: str, b: str) -> float | None:
    """Log-yüzde değişim; iki uç da TAM o günde ölçülmüş değilse None (Yahoo'da
    30.09.2026 New York kapanışı yok — bir önceki günün kuru ölçüyü iki güne
    yayardı)."""
    ta, va = _once(s, a)
    tb, vb = _once(s, b)
    if ta != a or tb != b:
        return None
    # Bayat bar: uç değer bir önceki barın BİREBİR aynısıysa kaynak o gün
    # kotasyon taşımamıştır (Yahoo çaprazlarında barların ~%0,9'u; 08.12.2011
    # EUR/GBP). Beş haneli bir kurda gerçek sıfır değişim bundan ayırt edilemez.
    for t_ in (ta, tb):
        i = s.index.get_loc(pd.Timestamp(t_))
        if i > 0 and float(s.iloc[i]) == float(s.iloc[i - 1]):
            return None
    return float(100 * (np.log(vb) - np.log(va)))


BETA_DONEM = [("2010–2012", "2010-01-01", "2012-12-31"), ("2013–2019", "2013-01-01", "2019-12-31"),
              ("2020–2023", "2020-01-01", "2023-12-31"), ("2024–2025", "2024-01-01", "2025-12-31"),
              ("2026 Ocak–Ağustos", "2026-01-01", "2026-08-31"), ("2026 Eylül", "2026-09-01", "2026-09-30")]
BETA_ULKE = ("fr", "it", "at")


def beta() -> dict:
    """10 yıllık getirinin Bund'a duyarlılığı (günlük değişimler):
    ΔX = a + b·ΔBund. Beta İKİ rejimde iki ayrı şey söyler: küresel faiz
    satışında b > 1 Bund yükselirken farkın da açılması demektir (yüksek beta);
    riskten kaçışta Bund düşerken getirisi yükselen tahvilin betası düşük ya da
    EKSİdir (2010–2012 çevre imzası). Tek bir eşik iki rejimi ayırmaz: İtalya
    2013–2019'da 0,40 ile "1'in altında" kalır, ama çekirdek değildir. Çekirdek
    kıyas olarak Avusturya yazılır (Hollanda serisi 2014 sonunda başlıyor). Günlük: kısa pencerede haftalık örneklem
    yetmez. Eylül penceresi 30 Eylül'de biter (22 iş günü); 1 Ekim'in tek günü
    (Bund −6, OAT +8,6) betayı tek başına 0,24 düşürüyordu."""
    df = gunluk()
    d = df[[f"{u}10y" for u in BETA_ULKE] + ["de10y"]].diff() * 100
    out = {"donemler": []}
    for ad, a, b in BETA_DONEM:
        dd = d[(d.index >= a) & (d.index <= b)]
        r = {"ad": ad, "n": int(len(dd.dropna(subset=["fr10y", "de10y"])))}
        for u in BETA_ULKE:
            o = ols(dd, f"{u}10y", ["de10y"], nw=2)
            r[f"{u}_b"], r[f"{u}_t"] = o["b"]["de10y"], o["t"]["de10y"]
        out["donemler"].append(r)
    dd = d[(d.index >= "2026-09-01") & (d.index <= SON_GUN)]
    o = ols(dd, "fr10y", ["de10y"], nw=2)
    out["eylul_1ekim"] = {"n": int(len(dd.dropna(subset=["fr10y", "de10y"]))), "fr_b": o["b"]["de10y"]}
    # Birinci evrede (31.08 → 28.09) Bund'un yükselişinin farka katkısı:
    # (b − 1)·ΔBund, iki betayla: evre ÖNCESİ (Ocak–Ağustos) ve evrenin KENDİSİ.
    ev = evreler()[0]
    dd = d[(d.index > ev["bas"]) & (d.index <= ev["son"])].dropna(subset=["fr10y", "de10y"])
    b_ic = ols(dd, "fr10y", ["de10y"], nw=2)
    b_once = next(r["fr_b"] for r in out["donemler"] if r["ad"] == "2026 Ocak–Ağustos")
    out["evre1"] = {"bas": ev["bas"], "son": ev["son"], "de": ev["de10y_bp"], "spr": ev["fr"],
                    "beta_once": b_once, "beta_ic": b_ic["b"]["de10y"], "beta_ic_t": b_ic["t"]["de10y"],
                    "beta_ic_n": b_ic["n"], "pay_once": (b_once - 1) * ev["de10y_bp"],
                    "pay_ic": (b_ic["b"]["de10y"] - 1) * ev["de10y_bp"]}
    ev2 = evreler()[1]
    out["evre2"] = {"bas": ev2["bas"], "son": ev2["son"], "de": ev2["de10y_bp"], "fr": ev2["fr10y_bp"],
                    "spr": ev2["fr"]}
    return out


GOSTERGE_SICRAMA = ("2017-10-09", "2022-11-28", "2022-11-30")


def hiz(vadeler=(10, 2)) -> dict:
    """Pencereli açılma (5 · 22 · 66 iş günü) ve bu büyüklüğün en son ne zaman
    görüldüğü. Pencereli ölçü tek günlük gösterge kaydırmalarına dayanıklıdır
    (CNBC serisinde gösterge tahvil değişimi tek günlük sıçrama üretebiliyor:
    28.11.2022 +16,2 bp, iki gün sonra −15,6 bp, ECB eğrisinde karşılığı yok);
    aynı epizodun kendi günleri sayılmaz (pencerenin 1,5 katı kadar geri gidilir)."""
    out = {}
    for v in vadeler:
        s = spread("fr", v)
        for n in (1, 5, 22, 66):
            g = s.diff(n).dropna()
            son = float(g.iloc[-1])
            once = g[g.index < g.index[-1] - pd.Timedelta(days=max(3, int(n * 1.5)))]
            ust = once[once >= son]
            out[f"{v}y_{n}"] = {"degisim": son, "son_gorulme": str(ust.index[-1].date()) if len(ust) else None}
    # Tek günlük ölçü gösterge değişimine karşı korumasız: bu günlerde Fransa
    # 10y bacağı sıçrarken aynı ülkenin 5 ve 30 yıllığı ile Almanya bacağı ters
    # yönde ya da çok az hareket ediyor (09.10.2017: 10y +13,5 bp, 5y −4,7, 30y
    # −1,9, Almanya −1,7 — yeni gösterge kâğıdı; 28.11.2022 +16,2, iki gün sonra
    # −15,6). Bu günler dışarıda bırakılarak "bugünkü kadar büyük tek günlük
    # açılma en son ne zaman" sorulur ve imza her koşuda yeniden sınanır.
    df = gunluk()
    s = spread("fr", 10)
    d = s.diff().dropna()
    for g in GOSTERGE_SICRAMA:
        i = df.index.get_loc(pd.Timestamp(g))
        f10 = (df["fr10y"].iloc[i] - df["fr10y"].iloc[i - 1]) * 100
        f30 = (df["fr30y"].iloc[i] - df["fr30y"].iloc[i - 1]) * 100
        if abs(f10) < 10 or abs(f30) > abs(f10) / 2:
            raise ArsivHatasi(f"gösterge sıçraması imzası tutmuyor: {g} 10y {f10:.1f} 30y {f30:.1f}")
    temiz = d.drop(pd.to_datetime(GOSTERGE_SICRAMA), errors="ignore")
    ust = temiz[(temiz.index < temiz.index[-1]) & (temiz >= temiz.iloc[-1])]
    out["10y_1_gercek"] = {"degisim": float(temiz.iloc[-1]), "son_gorulme": str(ust.index[-1].date()),
                           "ayiklanan": list(GOSTERGE_SICRAMA)}
    # 2017 gösterge değişimi kalıcı bir seviye kaymasıdır: iki hafta sonra fark hâlâ yeni seviyede.
    i = s.index.get_loc(pd.Timestamp("2017-10-09"))
    out["sicrama_2017"] = {"once": float(s.iloc[i - 1]), "gun": float(s.iloc[i]), "on_gun_sonra": float(s.iloc[i + 9]),
                           "on_gun_sonra_tarih": str(s.index[i + 9].date())}
    k = s.index.get_loc(pd.Timestamp("2022-11-28"))
    out["sicrama_2022"] = {"once": float(s.iloc[k - 1]), "sonra": float(s.iloc[k + 2])}
    rd = ((df["us2y"] - df["de2y"]) * 100).dropna()
    out["rd_son"] = float(rd.iloc[-1])
    out["rd_atif_bas"] = _once(rd, ATIF_BAS)[1]
    return out


# ── 6. ne kadar gidebilir: ölçülmüş dağılımlar ───────────────────────────
def ileri_dagilim(esik: float = 30.0, pencere: int = 22, ufuk: int = 22) -> dict:
    """Spread son `pencere` iş gününde ≥ `esik` bp açıldığında, sonraki `ufuk`
    iş gününde ne oldu? Örtüşen gözlemler bağımsız değildir: gözlemler arasında
    40 takvim gününden uzun boşluk yeni bir KÜME açar ve kümeler adıyla yazılır
    — dağılımın hangi dönemden geldiği görünmezse tek bir epizot bütün oranı
    taşıyabilir."""
    s = spread()
    g = s.diff(pencere)
    ileri = s.shift(-ufuk) - s
    k = pd.DataFrame({"g": g, "i": ileri}).dropna()
    sec = k[k["g"] >= esik]
    kumeler, onceki = [], None
    for t, r in sec.iterrows():
        if onceki is None or (t - onceki).days > 40:
            kumeler.append([])
        kumeler[-1].append((t, r["g"], r["i"]))
        onceki = t
    kume = [{"bas": str(c[0][0].date()), "son": str(c[-1][0].date()), "n": len(c),
             "azami_acilma": float(max(x[1] for x in c)),
             "ileri_min": float(min(x[2] for x in c)), "ileri_maks": float(max(x[2] for x in c)),
             "ileri_medyan": float(np.median([x[2] for x in c])),
             "daha_acilan": int(sum(1 for x in c if x[2] > 0))} for c in kumeler]
    return {"esik": esik, "pencere": pencere, "ufuk": ufuk, "gozlem": int(len(sec)), "epizot": len(kume),
            "kumeler": kume,
            "daha_acildi_payi": float((sec["i"] > 0).mean() * 100) if len(sec) else None,
            "daha_acilan_kume": int(sum(1 for c in kume if c["daha_acilan"] > 0)),
            "medyani_artida_kume": int(sum(1 for c in kume if c["ileri_medyan"] > 0)),
            "kriz_disi_gozlem": int(((sec.index < "2011-01-01") | (sec.index > "2012-12-31")).sum()),
            "kriz_disi_daha_acilan": int(((sec["i"] > 0) & ((sec.index < "2011-01-01") | (sec.index > "2012-12-31"))).sum()),
            "medyan": float(sec["i"].median()) if len(sec) else None,
            "p10": float(sec["i"].quantile(0.1)) if len(sec) else None,
            "p90": float(sec["i"].quantile(0.9)) if len(sec) else None,
            "bugunku_acilma": float(g.iloc[-1])}


def oynaklik_bandi(gun: int = 20, ufuk: int = 22) -> dict:
    """Son `gun` iş gününün gerçekleşen günlük spread oynaklığı ve onun ±1,96σ√ufuk
    bandı. Tahmin değil, ölçek: bugünkü hızla bir ayda ne kadar yer değiştirir."""
    d = spread().diff().dropna()
    sig = float(d.iloc[-gun:].std(ddof=1))
    uzun = d[d.index >= "2013-01-01"]
    sig_uzun = float(uzun.std(ddof=1))
    # Gösterge sıçramaları ve 2014 boşluğunun geçiş farkları dışarıda (bir
    # günlük değişim değiller).
    temiz = uzun.drop(pd.to_datetime(GOSTERGE_SICRAMA + BOSLUK_GECIS), errors="ignore")
    sig_temiz = float(temiz.std(ddof=1))
    return {"sigma_gunluk": sig, "sigma_2013_sonrasi": sig_uzun, "oran": sig / sig_uzun,
            "sigma_2013_temiz": sig_temiz, "oran_temiz": sig / sig_temiz,
            "bant_1a": 1.96 * sig * np.sqrt(ufuk), "spread": float(spread().iloc[-1])}


# 2014'te kaynakta iki uzun boşluk var; boşluğun iki ucundaki fark bir
# günlük değişim değildir (67 ve 109 takvim günü).
BOSLUK_GECIS = ("2014-03-07", "2015-01-02")


def veri_bosluklari() -> dict:
    """Kaynağın kapsam boşlukları ve takvim tatilleri — ölçüldü, yazılır."""
    from dateutil.easter import easter
    s = spread()
    bd = pd.bdate_range(s.index[0], s.index[-1])
    eksik = bd.difference(s.index)
    y2014 = eksik[eksik.year == 2014]
    gec = {}
    for g in BOSLUK_GECIS:
        i = s.index.get_loc(pd.Timestamp(g))
        gec[g] = {"onceki": str(s.index[i - 1].date()), "gun": int((s.index[i] - s.index[i - 1]).days),
                  "fark": float(s.iloc[i] - s.iloc[i - 1])}
    tatil = []
    for y in range(int(s.index[0].year), int(s.index[-1].year) + 1):
        e = pd.Timestamp(easter(y))
        for t_ in (pd.Timestamp(f"{y}-01-01"), e - pd.Timedelta(days=2), e + pd.Timedelta(days=1),
                   pd.Timestamp(f"{y}-05-01"), pd.Timestamp(f"{y}-12-25"), pd.Timestamp(f"{y}-12-26")):
            if t_.dayofweek < 5 and s.index[0] <= t_ <= s.index[-1]:
                tatil.append(t_)
    kalan = [t_ for t_ in tatil if t_ in s.index]
    dd = s.diff()
    return {"eksik_is_gunu_2014": int(len(y2014)), "eksik_is_gunu_toplam": int(len(eksik)),
            "gecis": gec, "target_tatil": len(tatil), "target_tatil_seride": len(kalan),
            "target_tatil_mutlak_medyan": float(dd.reindex(kalan).abs().median()),
            "target_tatil_mutlak_maks": float(dd.reindex(kalan).abs().max())}


def gunluk_bar_saati() -> dict:
    """Günlük bar gün içinde hangi kotasyona denk geliyor? Her gün ve bacak için
    |günlük bar − 17:30'a kadarki son dakikalık kotasyon|, bp."""
    g = gun_ici()
    c = gunluk()
    out = {}
    for col in ("fr10y", "de10y", "it10y", "fr2y", "de2y", "us2y", "us10y"):
        fark = []
        for d in sorted(set(g.index.date)):
            ts = pd.Timestamp(str(d))
            if ts not in c.index or pd.isna(c.loc[ts, col]):
                continue
            x = g[(g.index.date == d) & (g.index.strftime("%H:%M") <= "17:30")][col].dropna()
            if len(x):
                fark.append(abs(float(c.loc[ts, col]) - float(x.iloc[-1])) * 100)
        out[col] = {"gun": len(fark), "medyan_bp": float(np.median(fark)), "maks_bp": float(max(fark))}
    return out


# ── 7. gün içi: 1 Ekim ────────────────────────────────────────────────────
PARIS = "Europe/Paris"


@lru_cache(maxsize=None)
def gun_ici() -> pd.DataFrame:
    """Dakikalık son kotasyonlar, Paris saatine çevrilmiş; her bacak kendi son
    kotasyonunu taşır (ileri doldurma yalnız AYNI GÜN içinde)."""
    g = oku("cnbc_gun_ici.csv.gz").copy()
    g.index = g.index.tz_localize("UTC").tz_convert(PARIS)
    g = g.sort_index()
    gun = g.index.date
    g = g.groupby(gun).ffill()
    g["spr"] = (g["fr10y"] - g["de10y"]) * 100
    g["ispr"] = (g["it10y"] - g["de10y"]) * 100
    g["spr2"] = (g["fr2y"] - g["de2y"]) * 100
    g["ispr2"] = (g["it2y"] - g["de2y"]) * 100
    g["rd"] = (g["us2y"] - g["de2y"]) * 100
    return g


def on_bes(gg: pd.DataFrame) -> pd.DataFrame:
    """15 dakikalık ızgara, "≤ t" kuralıyla: "15:30" noktası 15:30'a KADARKİ son
    kotasyondur (tablolar ve alt yazılarla aynı kural). Pandas'ın öntanımlısı
    (sol etiket) her noktaya etiketinden SONRAKİ 15 dakikanın son kotasyonunu
    yazar ve açılmayı olduğundan erken gösterir."""
    return gg.resample("15min", label="right", closed="right").last().ffill()


def gun_ici_pencere(gun: str = SON_GUN, bas: str = "15:30", son: str = "17:30") -> dict:
    """Bir gün içi pencerede farkların, faiz farkının ve kurun değişimi.

    Pencere VERİYE BAKILARAK seçildi (1 Ekim'de açılmanın başladığı saat →
    Avrupa kapanışı): bu bir sınama değil, bir olayın betimlemesidir. Faiz
    farkının kımıldamadığı bir pencerede kurun hareketi, faiz kanalına
    atfedilemeyecek kısmı GÖRÜNÜR kılar; büyüklüğü tek bir günden genellenmez."""
    g = gun_ici()
    gg = g[g.index.date == pd.Timestamp(gun).date()].between_time("08:00", "17:30")
    a = gg[gg.index.strftime("%H:%M") <= bas].iloc[-1]
    b = gg[gg.index.strftime("%H:%M") <= son].iloc[-1]
    out = {"gun": gun, "bas": bas, "son": son}
    for k in ("spr", "ispr", "spr2", "ispr2", "rd"):
        out[k] = {"bas": float(a[k]), "son": float(b[k]), "degisim": float(b[k] - a[k])}
    for k in ("de2y", "us2y", "de10y", "fr10y", "it2y"):
        out[k] = {"bas": float(a[k]), "son": float(b[k]), "degisim_bp": float((b[k] - a[k]) * 100)}
    out["eurusd"] = {"bas": float(a["eurusd"]), "son": float(b["eurusd"]),
                     "degisim_yuzde": float(100 * (np.log(b["eurusd"]) - np.log(a["eurusd"])))}
    return out


def gun_ici_ozet(gun: str = SON_GUN, saatler=("09:00", "14:15", "17:30")) -> dict:
    """Bir günün seçili saatlerindeki fark ve kur; 15 dakikalık değişimlerin
    eş hareketi. Avrupa seansı: 08:00–17:30 Paris."""
    g = gun_ici()
    gg = g[(g.index.date == pd.Timestamp(gun).date())]
    gg = gg.between_time("08:00", "17:30")
    out = {"gun": gun, "dakika": int(len(gg))}
    for s in saatler:
        r = gg[gg.index.strftime("%H:%M") <= s].iloc[-1]
        out[s] = {k: float(r[k]) for k in ("spr", "ispr", "spr2", "ispr2", "eurusd", "de10y", "fr10y", "de2y",
                                           "us2y", "rd")}
    zt = gg["spr"].idxmax()
    out["zirve"] = {"saat": zt.strftime("%H:%M"), "spr": float(gg["spr"].max())}
    # Günlük kapanış barı ile gün içi 17:30 kotasyonu arasındaki fark (bacak bacak).
    g0 = gunluk().loc[gun]
    out["gunluk_kapanis"] = {"spr": float((g0["fr10y"] - g0["de10y"]) * 100), "fr10y": float(g0["fr10y"]),
                             "de10y": float(g0["de10y"]), "de2y": float(g0["de2y"])}
    on5 = on_bes(gg).dropna(subset=["spr", "eurusd"])
    d = pd.DataFrame({"spr": on5["spr"].diff(), "fx": np.log(on5["eurusd"]).diff() * 100,
                      "ispr": on5["ispr"].diff()}).dropna()
    out["on5_n"] = int(len(d))
    out["on5_korelasyon"] = float(d["spr"].corr(d["fx"]))
    out["on5_egim"] = float(np.polyfit(d["spr"], d["fx"], 1)[0]) if len(d) > 3 else None
    return out


def gun_ici_bes_gun() -> dict:
    """Arşivdeki beş günün tamamında 15 dakikalık değişimlerin eş hareketi
    (Avrupa seansı); her gün ayrı ve birleşik."""
    g = gun_ici()
    parca, gunluk_k = [], {}
    for gun in sorted(set(g.index.date)):
        gg = g[g.index.date == gun].between_time("08:00", "17:30")
        on5 = on_bes(gg).dropna(subset=["spr", "eurusd", "rd"])
        d = pd.DataFrame({"spr": on5["spr"].diff(), "rd": on5["rd"].diff(),
                          "fx": np.log(on5["eurusd"]).diff() * 100}).dropna()
        if len(d) >= 10:
            gunluk_k[str(gun)] = {"n": int(len(d)), "korelasyon": float(d["spr"].corr(d["fx"]))}
            parca.append(d.assign(gun=str(gun)))
    b = pd.concat(parca)
    # Faiz farkı kontrollü: 15 dakikalık kur değişimi ~ fark + faiz farkı.
    k = ols(b, "fx", ["spr", "rd"], nw=2)
    k1 = ols(b[b["gun"] != SON_GUN], "fx", ["spr", "rd"], nw=2)
    return {"gunler": gunluk_k, "n": int(len(b)), "korelasyon": float(b["spr"].corr(b["fx"])),
            "egim": float(np.polyfit(b["spr"], b["fx"], 1)[0]), "kontrollu": k, "kontrollu_1ekim_haric": k1}


# ── 8. kayan katsayı ──────────────────────────────────────────────────────
def kayan_katsayi(pencere: int = 104, y: str = "fx") -> pd.DataFrame:
    """`pencere` haftalık kayan pencerede kurun faiz farkı ve OAT–Bund farkına
    duyarlılığı (10 bp başına %), Newey–West ±2 s.h. bandıyla. Tarih pencerenin
    BİTİŞİdir: 2024'te biten bir pencere 2022–2023'ü taşır."""
    d = haftalik()
    sat = []
    for i in range(pencere, len(d) + 1):
        dd = d.iloc[i - pencere:i]
        o = ols(dd, y, ["rd", "spr"])
        b, t = o["b"]["spr"] * 10, o["t"]["spr"]
        se = abs(b / t) if t else float("nan")
        sat.append({"tarih": dd.index[-1], "spr": b, "alt": b - 2 * se, "ust": b + 2 * se,
                    "rd": o["b"]["rd"] * 10})
    return pd.DataFrame(sat).set_index("tarih")


def kayan_ozet(kk: pd.DataFrame) -> dict:
    """Kayan katsayının işaret rejimleri: pozitif koşular (fark açılırken kurun
    YÜKSELDİĞİ pencereler) adıyla yazılır."""
    poz = kk["spr"] > 0
    kos, bas = [], None
    for tt, v in poz.items():
        if v and bas is None:
            bas = tt
        if not v and bas is not None:
            kos.append((bas, onceki))
            bas = None
        onceki = tt
    if bas is not None:
        kos.append((bas, onceki))
    uzun = [(a, b) for a, b in kos if (b - a).days >= 90]
    return {"pencere_n": int(len(kk)), "pozitif_n": int(poz.sum()),
            "anlamli_eksi_n": int((kk["ust"] < 0).sum()),
            "pozitif_kosular": [(str(a.date()), str(b.date())) for a, b in uzun]}


def epizot_yollari(gun: int = 160) -> dict:
    """Her epizotta başlangıçtan itibaren farkın yolu; x ekseni takvim iş günü
    (np.busday_count, tablodaki 'iş günü' sütunuyla aynı sayım), gözlem sırası
    değil — eksik kotasyon günleri ekseni kaydırmasın."""
    s = spread()
    out = {}
    for ad, a, b, _ in EPIZOTLAR:
        p = s[s.index >= a]
        x = [_isgunu(str(p.index[0].date()), str(t.date())) for t in p.index]
        k = [i for i, v in enumerate(x) if v <= gun]
        out[ad] = {"x": [x[i] for i in k], "y": [round(float(p.iloc[i] - p.iloc[0]), 2) for i in k]}
    return out


# ── 10. öbür piyasalar ────────────────────────────────────────────────────
PIYASA = [("eurchf", "EUR/CHF"), ("eurjpy", "EUR/JPY"), ("eurgbp", "EUR/GBP"), ("dxy", "Dolar endeksi (DXY)"),
          ("vix", "VIX"), ("sx5e", "Euro Stoxx 50"), ("cac", "CAC 40"), ("dax", "DAX"),
          ("bnp", "BNP Paribas"), ("socgen", "Société Générale"), ("cagri", "Crédit Agricole")]


DOVIZ = ("eurchf", "eurjpy", "eurgbp")


def piyasalar(bas: str = ATIF_BAS) -> list[dict]:
    """Eylül penceresinde öbür piyasalar (Yahoo). Döviz çaprazları New York
    kapanışına hizalanır ve LOG değişimle yazılır (EUR/USD ile aynı sözleşme);
    öbürleri basit yüzde değişim."""
    y = oku("yahoo_gunluk.csv.gz")
    out = []
    for k, ad in PIYASA:
        if k not in y:
            continue
        if k in DOVIZ:
            s = yahoo_ny(k)
            deg = lambda a, b: float(100 * (np.log(b) - np.log(a)))
        else:
            s = y[k].dropna()
            s = s[s.index <= SON_GUN]
            deg = lambda a, b: float(100 * (b / a - 1))
        out.append({"kod": k, "ad": ad, "log": k in DOVIZ, "son": float(s.iloc[-1]),
                    "son_gun": str(s.index[-1].date()), "bas_gun": _once(s, bas)[0],
                    "degisim": deg(_once(s, bas)[1], float(s.iloc[-1])),
                    "degisim_haziran": deg(_once(s, "2026-06-30")[1], float(s.iloc[-1]))})
    return out


def kur_ozeti() -> dict:
    """EUR/USD seviyeleri (New York kapanışı) ve aynı günün ECB kuru."""
    fx = kur_ny()
    ecb = oku("eurusd_ecb.csv.gz")["eurusd_ecb"].dropna()
    y26 = fx[fx.index >= "2026-01-01"]
    once = fx[fx.index < fx.index[-1]]
    alt = once[once <= fx.iloc[-1]]
    return {"son": float(fx.iloc[-1]), "gun": str(fx.index[-1].date()),
            "yil_zirve": float(y26.max()), "yil_zirve_gun": str(y26.idxmax().date()),
            "yil_dip": float(y26.min()), "yil_dip_gun": str(y26.idxmin().date()),
            "son_gorulme": str(alt.index[-1].date()) if len(alt) else None,
            "atif_bas": _once(fx, ATIF_BAS)[1], "haziran": _once(fx, "2026-06-30")[1],
            "yb": _once(fx, "2025-12-31")[1], "onceki_gun": float(fx.iloc[-2]),
            "zirveden": float(100 * (np.log(fx.iloc[-1]) - np.log(y26.max()))),
            "ecb_son": _once(ecb, SON_GUN)[1], "ecb_gun": _once(ecb, SON_GUN)[0]}


def ecb_faiz() -> list[dict]:
    d = oku("ecb_dfr.csv.gz")["dfr"]
    d = d[d.index <= SON_GUN]
    ch = d[d.diff() != 0]
    return [{"gun": str(t.date()), "dfr": float(v)} for t, v in ch[ch.index >= "2024-01-01"].items()]


# ── 9. ölçüm dosyası ──────────────────────────────────────────────────────
def _yuvarla(x, b: int = 6):
    if isinstance(x, float):
        return None if (x != x) else round(x, b)
    if isinstance(x, (np.floating,)):
        return _yuvarla(float(x), b)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, dict):
        return {str(k): _yuvarla(v, b) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_yuvarla(v, b) for v in x]
    return x


def _seri(s: pd.Series, b: int = 4) -> dict:
    s = s.dropna()
    return {"t": [str(t.date()) for t in s.index], "v": [round(float(v), b) for v in s.values]}


def hepsi() -> dict:
    """Yazının ve figürlerin bütün sayıları. `veri/olcum.json` olarak yazılır;
    yayın kapısı (dogrula.py) ve çizim (sekil.py) yalnız bunu okur."""
    s = spread()
    df = gunluk()
    D = duyarlilik()
    kk = kayan_katsayi()
    kg = kayan_katsayi(y="gbpusd")
    ke = kayan_katsayi(y="eurgbp")
    gi = gun_ici()
    gg = gi[gi.index.date == pd.Timestamp(SON_GUN).date()].between_time("07:30", "19:00")
    gg15 = on_bes(gg)
    hz = hiz()
    bugun_hiz = hz["10y_22"]["degisim"]
    out = {
        "son_gun": SON_GUN,
        "arsiv": {ad: v["sha256"] for ad, v in kunye()["dosyalar"].items()},
        "arsiv_olusturma": kunye()["olusturma"],
        "temizlik": temizlik_sayimi(),
        "bosluk": veri_bosluklari(),
        "bar_saati": gunluk_bar_saati(),
        "seviye": seviye_ozeti(),
        "kaynak": kaynak_sinamasi(),
        "akranlar": akranlar(),
        "fransa_italya": fransa_italya(),
        "egri": egri(),
        "hiz": hz,
        "yahoo_hiza": _yahoo_hiza(),
        "capraz": capraz_ayrisma(),
        "evreler": evreler(),
        "bacaklar": bacaklar(),
        "buyuk_gunler": buyuk_gunler(),
        "atif_duyarlilik": {y: atif_duyarlilik(y=y) for y in ("fx", "gbpusd", "eurgbp", "eurchf")},
        "beta": beta(),
        "olay_tepkileri": olay_tepkileri(),
        "ayrisma": ayrisma_ornekleri(),
        "epizotlar": epizotlar(),
        "duyarlilik": D,
        "kanallar": kanallar(),
        "orneklem_disi": {y: {"2004_2023": orneklem_disi("2023-12-31", "2004-01-01", y),
                              "2013_2023": orneklem_disi("2023-12-31", "2013-01-01", y),
                              "2004_2019": orneklem_disi("2019-12-31", "2004-01-01", y)}
                          for y in ("fx", "fx_ecb", "gbpusd", "eurgbp")},
        "atif": {"eylul": {y: epizot_atfi(y=y) for y in ("fx", "gbpusd", "eurgbp", "eurchf")},
                 "yaz": {y: epizot_atfi(bas="2026-06-30", son=ATIF_BAS, kesim="2026-06-29", y=y)
                         for y in ("fx", "gbpusd", "eurgbp")}},
        "ileri": [ileri_dagilim(30, 22, 22), ileri_dagilim(30, 22, 66), ileri_dagilim(40, 22, 22),
                  ileri_dagilim(50, 22, 22), ileri_dagilim(bugun_hiz, 22, 22)],
        "oynaklik": oynaklik_bandi(),
        "gun_ici": gun_ici_ozet(),
        "gun_ici_pencere": gun_ici_pencere(),
        "gun_ici_pencere_1600": gun_ici_pencere(bas="16:00"),
        "gun_ici_ism": gun_ici_pencere(bas="15:45", son="16:00"),
        "gun_ici_bes_gun": gun_ici_bes_gun(),
        "piyasalar": piyasalar(),
        "kur": kur_ozeti(),
        "ecb_faiz": ecb_faiz(),
        "kayan": {"son": float(kk["spr"].iloc[-1]), "son_alt": float(kk["alt"].iloc[-1]),
                  "son_ust": float(kk["ust"].iloc[-1]), "son_tarih": str(kk.index[-1].date()),
                  "ort_2013_2019": float(kk.loc["2013":"2019", "spr"].mean()),
                  "ort_2024_sonra": float(kk.loc["2024":, "spr"].mean()), **kayan_ozet(kk),
                  "gbp_son": float(kg["spr"].iloc[-1]), "gbp_son_alt": float(kg["alt"].iloc[-1]),
                  "gbp_son_ust": float(kg["ust"].iloc[-1]),
                  "eurgbp_son": float(ke["spr"].iloc[-1]), "eurgbp_son_alt": float(ke["alt"].iloc[-1]),
                  "eurgbp_son_ust": float(ke["ust"].iloc[-1])},
        "seriler": {
            "spread": _seri(s, 2),
            "spread_it": _seri(spread("it"), 2),
            "fr10": _seri(df["fr10y"], 4), "de10": _seri(df["de10y"], 4),
            "kayan": {"t": [str(t.date()) for t in kk.index], "spr": [round(float(v), 4) for v in kk["spr"]],
                      "alt": [round(float(v), 4) for v in kk["alt"]], "ust": [round(float(v), 4) for v in kk["ust"]],
                      "eurgbp": [round(float(v), 4) for v in ke["spr"]],
                      "eurgbp_alt": [round(float(v), 4) for v in ke["alt"]],
                      "eurgbp_ust": [round(float(v), 4) for v in ke["ust"]]},
            "epizot_yollari": epizot_yollari(),
            "gun_ici": {"t": [t.strftime("%H:%M") for t in gg15.index],
                        "spr": [None if v != v else round(float(v), 2) for v in gg15["spr"]],
                        "ispr2": [None if v != v else round(float(v), 2) for v in gg15["ispr2"]],
                        "spr2": [None if v != v else round(float(v), 2) for v in gg15["spr2"]],
                        "eurusd": [None if v != v else round(float(v), 5) for v in gg15["eurusd"]],
                        "rd": [None if v != v else round(float(v), 2) for v in gg15["rd"]]},
            "ileri_noktalar": _ileri_noktalar(),
        },
    }
    return _yuvarla(out)


def _ileri_noktalar(esik: float = 30.0, pencere: int = 22, ufuk: int = 22) -> dict:
    s = spread()
    k = pd.DataFrame({"g": s.diff(pencere), "i": s.shift(-ufuk) - s}).dropna()
    sec = k[k["g"] >= esik]
    return {"t": [str(t.date()) for t in sec.index], "g": [round(float(v), 2) for v in sec["g"]],
            "i": [round(float(v), 2) for v in sec["i"]]}


def main() -> int:
    o = hepsi()
    (VERI / "olcum.json").write_text(json.dumps(o, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")
    sv = o["seviye"]
    print(f"olcum.json yazıldı · veri günü {o['son_gun']} · fark {sv['spread']:.1f} bp · "
          f"{len(o['seriler']['spread']['t'])} gün")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
