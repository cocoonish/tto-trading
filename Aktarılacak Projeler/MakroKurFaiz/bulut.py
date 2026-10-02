#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — bulut arşivinin OKUYUCULARI (tek arayüz).

Ham yanıtlar `veri/ham/` altındadır (arsiv_makro.py, bulutta); ayrıştırılmış
hâlleri `veri/bulut/*.csv.gz` (hazirla_bulut.py, yerelde) ve aynı sha256
kapısından okunur (`ortak_olc.oku`). Bölüm modülleri bulut verisine YALNIZ bu
dosyanın fonksiyonlarıyla erişir: dönüş biçimi burada sözleşmedir, dosya adı
ve sütun adı bir kez yazılır.

Kaynak gelmediyse ya da ayrıştırılmadıysa fonksiyon `VeriYok` yükseltir ve
sebep metni okura yazılabilir; modül o pratiği "kurulmadı" diye döndürür
(uydurma yok: bulunamayan seri yerine sayı konmaz).
"""
from __future__ import annotations

import pandas as pd

import ortak_olc as oo


class VeriYok(RuntimeError):
    """Bulut kaynağı yok ya da ayrıştırılamadı; mesaj okur diliyle sebeptir."""


def _oku(ad: str, kaynak: str) -> pd.DataFrame:
    p = oo.BULUT / f"{ad}.csv.gz"
    if not p.exists():
        raise VeriYok(f"{kaynak} arşivi elde yok")
    return oo.oku(ad, oo.BULUT)


# ───────────────────────────────────────────────────────────── yayım takvimleri
def _takvim(ad: str, kaynak: str, bulten: str | None = None) -> pd.DatetimeIndex:
    df = _oku(ad, kaynak)
    if bulten is not None:
        df = df[df["bulten"] == bulten]
    idx = pd.DatetimeIndex(sorted(set(df.index.normalize())))
    if not len(idx):
        raise VeriYok(f"{kaynak}: {bulten or ''} için tarih bulunamadı")
    return idx


def tufe_gunleri() -> pd.DatetimeIndex:
    """TÜİK TÜFE bülteninin yayım günleri (10:00 TSİ). Kaynak: TÜİK yıllık haber bülteni listesi."""
    return _takvim("tuik_takvim", "TÜİK yayım takvimi", "tufe")


def gsyh_gunleri() -> pd.DatetimeIndex:
    """TÜİK çeyreklik GSYH bülteninin yayım günleri."""
    return _takvim("tuik_takvim", "TÜİK yayım takvimi", "gsyh")


def abd_istihdam_gunleri() -> pd.DatetimeIndex:
    """BLS Employment Situation yayım günleri (08:30 New York)."""
    return _takvim("bls_takvim", "BLS yayım arşivi", "empsit")


def abd_tufe_gunleri() -> pd.DatetimeIndex:
    """BLS CPI yayım günleri (08:30 New York)."""
    return _takvim("bls_takvim", "BLS yayım arşivi", "cpi")


def fomc_gunleri() -> pd.DatetimeIndex:
    """FOMC karar günleri (toplantının son günü; planlı toplantılar)."""
    return _takvim("fomc_takvim", "Federal Reserve FOMC takvimi")


def not_kararlari() -> pd.DataFrame:
    """Türkiye kredi notu kararları: index tarih; sütunlar kurum, eylem (not · görünüm), yon (+1/0/−1), aciklama."""
    return _oku("not_kararlari", "HMB kredi notu sayfası")


# ───────────────────────────────────────────────────────────── EVDS (bulut)
def pka_toplanti_beklentisi() -> pd.DataFrame:
    """Piyasa Katılımcıları Anketi: sıradaki PPK toplantısı için politika faizi
    beklentisi (%, medyan/ortalama hangisi yayımlanıyorsa adıyla). index anket
    dönemi (ay başı); sütun `politika_beklenti`, ayrıca `seri` (EVDS kodu)."""
    return _oku("evds_pka_toplanti", "EVDS Piyasa Katılımcıları Anketi")


def pka_kur_beklentisi() -> pd.DataFrame:
    """PKA USD/TRY beklentileri: index anket dönemi; sütunlar `usdtry_yilsonu`
    ve/veya `usdtry_12a` (yalnız gelenler)."""
    return _oku("evds_pka_kur", "EVDS Piyasa Katılımcıları Anketi")


def dis_ticaret_endeks() -> pd.DataFrame:
    """Dış ticaret birim değer ve miktar endeksleri (aylık): sütunlar
    `ihr_birim_deger`, `ith_birim_deger`, `ihr_miktar`, `ith_miktar`."""
    return _oku("evds_dis_ticaret_endeks", "EVDS dış ticaret endeksleri")


def kalan_vade_borc() -> pd.Series:
    """Kalan vadeye göre kısa vadeli dış borç stoku (milyon ABD doları)."""
    return _oku("evds_kalan_vade", "EVDS kalan vadeye göre dış borç")["kv_borc_mn_usd"].dropna()


def uyp() -> pd.DataFrame:
    """Uluslararası yatırım pozisyonu (çeyreklik, milyon ABD doları):
    `varlik`, `yukumluluk`, `net`."""
    return _oku("evds_uyp", "EVDS uluslararası yatırım pozisyonu")


# ───────────────────────────────────────────────────────────── uluslararası
def bis_reer(tur: str = "R") -> pd.DataFrame:
    """BIS geniş efektif kur (aylık; R reel, N nominal). Sütunlar ISO2 ülke
    kodları; ARTIŞ yerel paranın DEĞER KAZANCI (BIS yönü)."""
    return _oku(f"bis_eer_{tur.lower()}", "BIS efektif kur")


def bis_politika() -> pd.DataFrame:
    """BIS politika faizleri (aylık, ay sonu, %). Sütunlar ISO2 ülke kodları."""
    return _oku("bis_politika", "BIS politika faizi")


def ecb_kur(kod: str) -> pd.Series:
    """ECB euro referans kuru (14:15 CET), 1 euro = x birim `kod`."""
    df = _oku("ecb_kur", "ECB referans kurları")
    if kod.lower() not in df.columns:
        raise VeriYok(f"ECB referans kurları: {kod} elde yok")
    return df[kod.lower()].dropna()


def eurostat_borc() -> dict:
    """Eurostat genel yönetim, % GSYH, yıllık: {'borc': df, 'denge': df};
    sütunlar ülke kodları (Eurostat: EL Yunanistan)."""
    df = _oku("eurostat_borc", "Eurostat genel yönetim")
    out = {}
    for k in ("borc", "denge"):
        alt = df[[c for c in df.columns if c.startswith(k + "_")]]
        out[k] = alt.rename(columns=lambda c: c.split("_", 1)[1])
    return out


def wdi(gosterge: str) -> pd.DataFrame:
    """Dünya Bankası WDI göstergesi (yıllık); sütunlar ISO3 ülke kodları."""
    ad = {"cari": "wdi_cari", "borc": "wdi_borc", "buyume": "wdi_buyume", "enflasyon": "wdi_enflasyon"}[gosterge]
    return _oku(ad, "Dünya Bankası WDI")


def acm() -> pd.DataFrame:
    """NY Fed ACM vade primi ve getirileri (günlük): `acmtp02`, `acmtp10`,
    `acmy10`, `acmrny10` (risk-nötr getiri) — gelenler."""
    return _oku("acm", "NY Fed ACM vade primi")


def abd_1y() -> pd.Series:
    """ABD Hazinesi 1 yıllık par getirisi (günlük, %)."""
    return _oku("abd_hazine_1y", "ABD Hazinesi par getiri eğrisi")["us1y"].dropna()


def gilt() -> pd.DataFrame:
    """İngiltere gilt getirileri (günlük, %): `gb2y`, `gb10y`, `gb30y` — gelenler."""
    return _oku("gilt", "gilt getirileri")
