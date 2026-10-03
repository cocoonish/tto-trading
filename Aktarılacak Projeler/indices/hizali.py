"""Haber endeksini FIYATLA kiyaslamanin ortak zemini — kalibrasyon ve figurler buradan.

Uc kural tek yerde:
  1. ARSIV. Haftalik haber onbelleginden (data/gdelt_cache.json) son KAPANMIS
     52 hafta; yalniz skorlanmis makaleler; tahvilde skor terslenmis KOPYA
     (onbellek degismez). Yayim damgasi kendi haftasinin disina dusen makale
     ATILIR ve sayisi yazilir: RSS kaydinda tarih yoksa `news_fetcher` cekim
     anini yazar, o makale baska bir haftanin penceresine girerdi.
  2. GUN. Bir islem gunu ancak kapanis ani arsivin icindeyse ve 7 gunluk pencere
     arsivin basindan sonra basliyorsa olculur (yarim pencere yarim olcudur).
  3. DEGER. Fiyatla kiyaslanan deger CANLI ENDEKSIN KENDISIDIR: o gunun kapanis
     aninda `_compute_index_value` (normalizasyon, tanh ve EMA YOK — okurun
     gordugu sayi budur). Pencerede makale yoksa NaN (olculemeyen bos birakilir;
     sifir bir olcum sonucu degildir).
Gosterim serileri (rejim panelleri, Sekil 03'un cubuklari) z-skor + EMA ile
kurulur; onlar fiyatla KIYASLANMAZ.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import config
import index_builder

HAFTA = 52
ASGARI_CIFT = 20          # bundan az eksiksiz cift varsa korelasyon olculmez


# ─────────────────────────────────────────── 1 · arsiv
def arsiv(onbellek: dict, anahtar: str, simdi: datetime | None = None, hafta: int = HAFTA):
    """(makaleler, arsiv_bas, arsiv_son, denetim) — sira: en yeni hafta once,
    hafta ici kayitli sirayla (eski optimizasyonun sirasi)."""
    simdi = simdi or datetime.now(timezone.utc)
    kay = onbellek.get(anahtar) or {}
    kapali = []
    for k in kay:
        try:
            son = datetime.fromisoformat(k).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            continue
        if son < simdi:
            kapali.append(k)
    haftalar = sorted(kapali, reverse=True)[:hafta]
    ters = config.ASSETS.get(anahtar, {}).get("invert_sentiment", False)
    makaleler, disari, gece_yarisi, skorsuz = [], 0, 0, 0
    for h in haftalar:
        son = datetime.fromisoformat(h).replace(tzinfo=timezone.utc)
        bas = son - timedelta(days=6)
        bitis = son + timedelta(days=1)          # Pazar 24:00
        for a in kay[h].get("articles", []):
            if "score" not in a:
                skorsuz += 1
                continue
            try:
                pub = datetime.fromisoformat(a["published"])
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError, KeyError):
                disari += 1
                continue
            if not (bas <= pub < bitis):
                disari += 1
                continue
            if pub.hour == 0 and pub.minute == 0 and pub.second == 0 and pub.microsecond == 0:
                gece_yarisi += 1
            makaleler.append(dict(a, score=-a["score"]) if ters else a)
    if not haftalar:
        return makaleler, None, None, {"hafta": 0}
    abas = datetime.fromisoformat(min(haftalar)).replace(tzinfo=timezone.utc) - timedelta(days=6)
    ason = datetime.fromisoformat(max(haftalar)).replace(hour=23, minute=59, second=59,
                                                         tzinfo=timezone.utc)
    denetim = {"hafta": len(haftalar), "makale": len(makaleler), "hafta_disi_atilan": disari,
               "skorsuz": skorsuz, "gece_yarisi_damgali": gece_yarisi}
    return makaleler, abas, ason, denetim


# ─────────────────────────────────────────── 2 · gun
def gecerli_gunler(an: pd.Series, abas: datetime, ason: datetime) -> pd.Series:
    """Kapanis ani arsivin icinde, 7 gunluk penceresi tam olan gunler: gun → an."""
    an = an.dropna()
    bas, son = pd.Timestamp(abas), pd.Timestamp(ason)
    pen = pd.Timedelta(days=config.LOOKBACK_DAYS)
    return an[(an - pen >= bas) & (an <= son)]


# ─────────────────────────────────────────── 3 · deger
def ham_seri(dizi: index_builder.MakaleDizisi, params: dict, anlar: pd.Series) -> pd.Series:
    """Canli endeks, her gunun kapanis aninda; makalesiz gun NaN."""
    out = {}
    for gun, an in anlar.items():
        ref = an.to_pydatetime() if hasattr(an, "to_pydatetime") else an
        v, n = index_builder._compute_index_value(dizi.makaleler, params, reference_time=ref,
                                                  dizi=dizi)
        out[gun] = v if n else math.nan
    return pd.Series(out, dtype="float64")


# ─────────────────────────────────────────── istatistik
def _sira(x: np.ndarray) -> np.ndarray:
    from scipy.stats import rankdata
    return rankdata(x)


def spearman(x, y, asgari: int = ASGARI_CIFT) -> float:
    """Eksiksiz ciftlerde Spearman ρ; cift azsa ya da bir taraf sabitse NaN."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = ~(np.isnan(x) | np.isnan(y))
    if m.sum() < asgari:
        return math.nan
    rx, ry = _sira(x[m]), _sira(y[m])
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return math.nan
    return float(((rx - rx.mean()) * (ry - ry.mean())).mean() / (sx * sy))


def kismi_spearman(x, y, z, asgari: int = ASGARI_CIFT) -> float:
    """z'nin etkisi ayiklanmis Spearman: sira artiklarinin Pearson'u."""
    x, y, z = (np.asarray(v, float) for v in (x, y, z))
    m = ~(np.isnan(x) | np.isnan(y) | np.isnan(z))
    if m.sum() < asgari:
        return math.nan
    rx, ry, rz = _sira(x[m]), _sira(y[m]), _sira(z[m])
    def art(a):
        b = np.polyfit(rz, a, 1)
        return a - np.polyval(b, rz)
    ex, ey = art(rx), art(ry)
    if ex.std() == 0 or ey.std() == 0:
        return math.nan
    return float(np.corrcoef(ex, ey)[0, 1])


def yuvarlanan(x: pd.Series, y: pd.Series, pencere: int = 20) -> pd.Series:
    """Eksiksiz ciftler uzerinde yuvarlanan Pearson (figur icin; karnede kullanilmaz)."""
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < pencere:
        return pd.Series(dtype="float64")
    r = d["x"].rolling(pencere).corr(d["y"])
    return r[np.isfinite(r)]


def p_degeri(gercek: float, bos: np.ndarray) -> float:
    """(1 + b) / (1 + K): b = bos dagilimda gercegi esitleyen ya da asan cekilis.
    Gercek tum cekilisleri asarsa p = 1/(1+K) olur, ASLA sifir degil."""
    bos = np.asarray(bos, float)
    bos = bos[~np.isnan(bos)]
    if math.isnan(gercek) or not len(bos):
        return math.nan
    return float((1 + (bos >= gercek).sum()) / (1 + len(bos)))
