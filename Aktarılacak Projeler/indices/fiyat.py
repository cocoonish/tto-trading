"""Kapanis fiyatlari ve KAPANIS ANLARI — fiyatla kiyaslanan her sey buradan okur.

NEDEN VAR. Hat fiyati `yf.download(..., interval="1d")` ile okuyordu. Yahoo'nun
KAPANMIS gunluk doviz barinda "Close" o gunun KAPANISI degil BASINDAKI fiyattir
(Londra gece yarisi; 02.10.2026'da olculdu, bkz. ortak/fx_kapanis.py baslik
notu): D diye etiketlenen deger D−1'in New York kapanisina denk duser. Haber
endeksinin kalibrasyonu, Sekil 03'un fiyat cizgisi, Sekil 04'un ve Sekil 05'in
getirileri bu yuzden dovizde BIR GUN kaymis bir seriyle kuruluyordu.

IKI SEY DONER, IKISI DE AYNI KAYNAKTAN:
  * `seri` — islem gunu (tz'siz gun) → kapanis fiyati;
  * `an`   — ayni gun → kapanisin UTC ani. Fiyatla kiyaslanan duyarlilik bu anda
    kurulur (index_builder.seri_anlarda): D'nin degeri D'nin kapanisinda bilinen
    haberdir, kapanistan sonraki haber D'ye girmez. Gece yarisi referansi New York
    kapanisindan saatler sonradir ve D'nin ileri getirisine bakis-ileri tasirdi.

DOVIZ (`=X`): saatlik bardan, ortak tanimla (`fx_kapanis.saatlik_kapanislar`;
KARAR 02.10.2026: lira disi kurlar New York 17:00). Bir yillik pencere saatlik
barin 730 gunluk sinirinin icinde; gunluk bar duzeltmesine gerek yok.

OBUR ENSTRUMANLAR (vadeli, endeks): Yahoo gunluk bari o GUNUN kapanisidir
(bultenin sozlesmesi: bulten/piyasa.KAPANIS_UTC). Kapanis ani asagidaki
tablodadir ve SAATIN KENDISI OLCULEREK SECILIR (kesif_kalibrasyon.py, M1: gunluk
kapanisin hangi saatlik barla en yakin eslestigi). Tabloda olmayan sembol HATA
verir — sessizce gece yarisina dusmesin.

KAPANMAMIS SEANS. Kapanis ani gelmemis gun seriye girmez (bir olcum ancak kapanmis
bir seansi olcebilir). HAFTA SONU barlari duser (bu hattin 15 enstrumaninin hicbiri
hafta sonu islem gormez).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import pandas as pd

# Doviz disi enstrumanlarin kapanis ani: (saat dilimi, yerel saat).
# DEGERLER OLCUMLE SECILDI — bkz. kesif_kalibrasyon.py (M1) ve CLAUDE.md kaydi.
KAPANIS = {
    "GC=F": ("America/New_York", dt.time(17, 0)),
    "SI=F": ("America/New_York", dt.time(17, 0)),
    "ZT=F": ("America/New_York", dt.time(17, 0)),
    "ZN=F": ("America/New_York", dt.time(17, 0)),
    "^GSPC": ("America/New_York", dt.time(16, 0)),
    "XU100.IS": ("Europe/Istanbul", dt.time(18, 0)),
}
# Okura giden tanimdaki yer adi (fx_kapanis.KESIM_ADI ile ayni bicim: "New York 17:00").
YER = {"America/New_York": "New York", "Europe/Istanbul": "İstanbul"}
SAATLIK_DONEM = "730d"
GUNLUK_DONEM = "2y"


@dataclass
class Fiyat:
    seri: pd.Series          # gun (tz'siz Timestamp) → kapanis
    an: pd.Series            # gun → kapanis ani (UTC Timestamp)
    tanim: str               # okura giden tanim: "New York 17:00 (saatlik bar)" gibi
    kaynak: str              # "saatlik" | "gunluk"
    olculemeyen: list        # bari olup kapanisi kurulamayan gunler (yalniz doviz yolu)


def doviz_mu(ticker: str) -> bool:
    return ticker.upper().endswith("=X")


def _simdi(simdi) -> pd.Timestamp:
    t = pd.Timestamp(simdi or dt.datetime.now(dt.timezone.utc))
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _pencere(seri: pd.Series, an: pd.Series, gun: int | None, simdi: pd.Timestamp):
    if gun is None or not len(seri):
        return seri, an
    bas = (simdi.tz_convert(None).normalize() - pd.Timedelta(days=gun))
    tut = seri.index >= bas
    return seri[tut], an[tut]


def doviz_kapanislari(ticker: str, saatlik: pd.Series | None = None, simdi=None,
                      gun: int | None = 400) -> Fiyat:
    """Doviz: saatlik bardan kurulan gunluk kapanis (fx_kapanis tek tanimi)."""
    import fx_kapanis
    t = _simdi(simdi)
    if saatlik is None:
        saatlik = fx_kapanis.yfinance_saatlik([ticker], SAATLIK_DONEM).get(ticker)
    if saatlik is None or not len(saatlik):
        raise RuntimeError(f"{ticker}: saatlik bar alinamadi — gunluk bara DUSULMEZ "
                           "(dovizde gunluk barin kapanisi gunun basidir)")
    tur = fx_kapanis.kesim_turu(ticker)
    k = fx_kapanis.saatlik_kapanislar(saatlik, tur, simdi=t.to_pydatetime())
    seri = k.seri.astype("float64")
    seri.index = pd.DatetimeIndex(seri.index).normalize()
    an = pd.Series({pd.Timestamp(g): pd.Timestamp(v.replace("Z", "+00:00"))
                    for g, v in k.kapanis_utc.items()})
    an = an.reindex(seri.index)
    seri, an = _pencere(seri, an, gun, t)
    return Fiyat(seri, an, f"{fx_kapanis.KESIM_ADI[tur]} (saatlik bar)", "saatlik",
                 list(k.olculemeyen))


def gunluk_kapanislar(ticker: str, gunluk: pd.Series | None = None, simdi=None,
                      gun: int | None = 400) -> Fiyat:
    """Doviz disi: Yahoo gunluk bari; kapanis ani KAPANIS tablosundan."""
    if ticker not in KAPANIS:
        raise KeyError(f"{ticker}: kapanis ani tanimsiz (fiyat.KAPANIS) — once olculmeli")
    t = _simdi(simdi)
    if gunluk is None:
        import yfinance as yf
        df = yf.download(ticker, period=GUNLUK_DONEM, interval="1d", auto_adjust=True,
                         progress=False)
        if df is None or df.empty:
            raise RuntimeError(f"{ticker}: gunluk bar alinamadi")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        gunluk = df["Close"]
    s = pd.to_numeric(gunluk, errors="coerce").dropna().astype("float64")
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    s.index = idx.normalize()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s = s[s.index.dayofweek < 5]                    # hafta sonu bari isleme ait degil
    tz, saat = KAPANIS[ticker]
    an = pd.Series([pd.Timestamp(dt.datetime.combine(g.date(), saat), tz=ZoneInfo(tz))
                    .tz_convert("UTC") for g in s.index], index=s.index)
    tut = an <= t                                    # kapanis ani gelmemis gun seriye girmez
    s, an = s[tut], an[tut]
    s, an = _pencere(s, an, gun, t)
    yerel = f"{YER.get(tz, tz)} {saat.strftime('%H:%M')}"
    return Fiyat(s, an, f"{yerel} (günlük bar)", "gunluk", [])


def kapanislar(ticker: str, simdi=None, gun: int | None = 400) -> Fiyat:
    """Tek giris: dovizde saatlik bardan, obur enstrumanlarda gunluk bardan."""
    if doviz_mu(ticker):
        return doviz_kapanislari(ticker, simdi=simdi, gun=gun)
    return gunluk_kapanislar(ticker, simdi=simdi, gun=gun)


def ileri_getiri(seri: pd.Series, h: int) -> pd.Series:
    """F_h(D) = P(D+h)/P(D) − 1, D+h h'inci SONRAKI islem gunu. Son h gun NaN."""
    return seri.shift(-h) / seri - 1.0


def geri_getiri(seri: pd.Series, h: int) -> pd.Series:
    """B_h(D) = P(D)/P(D−h) − 1: D'de BITEN h gunluk hareket (tepki olcusu)."""
    return seri / seri.shift(h) - 1.0
