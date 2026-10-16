# -*- coding: utf-8 -*-
"""Sentetik 1 dakikalık bid/ask verisi — gerçek seans yapısıyla (testler için)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import zaman as z  # noqa: E402
from veri import Dakika  # noqa: E402


#: Sentetik takvim: (olay, yerel tarih, yerel saat, bölge). 2023-11 → 2024-02 penceresine düşer.
OLAYLAR = [
    ("FOMC_karar", "2023-11-01", "14:00", "America/New_York"), ("FOMC_basin", "2023-11-01", "14:30", "America/New_York"),
    ("BoE_karar", "2023-11-02", "12:00", "Europe/London"),
    ("NFP", "2023-11-03", "08:30", "America/New_York"), ("CPI", "2023-11-14", "08:30", "America/New_York"),
    ("NFP", "2023-12-08", "08:30", "America/New_York"), ("CPI", "2023-12-12", "08:30", "America/New_York"),
    ("FOMC_karar", "2023-12-13", "14:00", "America/New_York"), ("FOMC_basin", "2023-12-13", "14:30", "America/New_York"),
    ("ECB_karar", "2023-12-14", "14:15", "Europe/Berlin"), ("ECB_basin", "2023-12-14", "14:45", "Europe/Berlin"),
    ("BoE_karar", "2023-12-14", "12:00", "Europe/London"),
    ("NFP", "2024-01-05", "08:30", "America/New_York"), ("CPI", "2024-01-11", "08:30", "America/New_York"),
    ("ECB_karar", "2024-01-25", "14:15", "Europe/Berlin"), ("ECB_basin", "2024-01-25", "14:45", "Europe/Berlin"),
    ("FOMC_karar", "2024-01-31", "14:00", "America/New_York"), ("FOMC_basin", "2024-01-31", "14:30", "America/New_York"),
    ("BoE_karar", "2024-02-01", "12:00", "Europe/London"), ("NFP", "2024-02-02", "08:30", "America/New_York"),
]


def olaylar_uret(ek: bool = True) -> pd.DataFrame:
    """Takvim modülünün şemasıyla sentetik olay tablosu (UTC zoneinfo'dan).

    `ek`: kullanıcının ek dosyasındaki gibi takvim dışı bir olay tipi ("EK"), her salı ve
    perşembe 10:00 ET — haber stratejileri sentetik veride yeterli örnek görsün diye."""
    from zoneinfo import ZoneInfo
    satir = []
    liste = list(OLAYLAR)
    if ek:
        for g in pd.bdate_range("2023-11-06", "2024-02-02"):
            if g.weekday() in (1, 3):
                liste.append(("EK", g.strftime("%Y-%m-%d"), "10:00", "America/New_York"))
    for olay, tarih, saat, bolge in liste:
        utc = pd.Timestamp(f"{tarih} {saat}").tz_localize(ZoneInfo(bolge)).tz_convert("UTC")
        satir.append({"olay": olay, "tarih": tarih, "yerel_saat": saat, "bolge": bolge,
                      "utc_sn": int(utc.timestamp())})
    return pd.DataFrame(satir)


def dakika_uret(bas: str = "2023-11-01", gun: int = 70, tohum: int = 3, makas: float = 2.0,
                soklar: np.ndarray | None = None) -> Dakika:
    """Hafta içi FX günleri (17:00 ET → 17:00 ET), Londra/NY saatlerinde yüksek oynaklık.

    `soklar` (UTC epoch sn): her birinde bir sıçrama ve 15 dakika yüksek oynaklık —
    haber stratejilerinin sinyal üretebilmesi için (yönü rastgele)."""
    r = np.random.default_rng(tohum)
    gunler = pd.bdate_range(bas, periods=gun)
    parcalar = []
    for g in gunler:
        b0, b1 = z.islem_gunu_sinirlari(g.date())
        t = np.arange(int(b0.timestamp()), int(b1.timestamp()), 60, dtype=np.int64)
        parcalar.append(t)
    t = np.concatenate(parcalar)
    lon = pd.to_datetime(t, unit="s", utc=True).tz_convert(z.LONDRA)
    saat = lon.hour.to_numpy()
    oyn = np.where((saat >= 8) & (saat < 17), 3.0, 1.2)
    adim = r.normal(0, 1, len(t)) * oyn
    if soklar is not None:
        rs = np.random.default_rng(tohum + 1)
        for ts in np.asarray(soklar, dtype=np.int64):
            i = int(np.searchsorted(t, ts))
            if i < len(t) and t[i] == ts:
                adim[i:i + 15] *= 2.5
                sicrama = rs.choice([-1.0, 1.0]) * rs.uniform(30, 80)
                adim[i] += sicrama
                if rs.random() < 0.5 and i + 6 < len(t):     # yarısı geri döner (başarısız kırılım)
                    adim[i + 6] -= sicrama
    c = 110000 + np.cumsum(adim)
    o = np.concatenate([[110000.0], c[:-1]])
    h = np.maximum(o, c) + np.abs(r.normal(0, 1.0, len(t))) * oyn
    l = np.minimum(o, c) - np.abs(r.normal(0, 1.0, len(t))) * oyn
    o, h, l, c = (np.round(x) for x in (o, h, l, c))
    h = np.maximum.reduce([h, o, c])
    l = np.minimum.reduce([l, o, c])
    yari = makas / 2
    gun_et = z.islem_gunu(pd.to_datetime(t, unit="s", utc=True)).to_numpy().astype("datetime64[D]")
    return Dakika("EURUSD", 10, t, o - yari, h - yari, l - yari, c - yari, o + yari, h + yari, l + yari, c + yari,
                  o, h, l, c, r.uniform(1, 5, len(t)), gun_et)


def boz(d: Dakika, sonra_t: int, tohum: int = 99) -> Dakika:
    """`sonra_t`'den sonraki fiyatları bambaşka bir yürüyüşle değiştirir (geçmiş aynı)."""
    r = np.random.default_rng(tohum)
    i = int(np.searchsorted(d.t, sonra_t, side="left"))
    n = len(d.t) - i
    kay = np.cumsum(r.normal(0, 8.0, n))
    ek = lambda x: np.concatenate([x[:i], x[i:] + kay])  # noqa: E731
    return Dakika(d.cift, d.pip, d.t, ek(d.bo), ek(d.bh), ek(d.bl), ek(d.bc), ek(d.ao), ek(d.ah), ek(d.al), ek(d.ac),
                  ek(d.mo), ek(d.mh), ek(d.ml), ek(d.mc), d.v, d.gun)
