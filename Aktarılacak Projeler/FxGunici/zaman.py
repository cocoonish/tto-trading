#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zaman katmanı: veri UTC'de durur, seanslar YEREL saatlerinde tanımlanır.

İlke. Bir seansın saati sabit bir UTC saati değildir: Londra 08:00 yazın 07:00,
kışın 08:00 UTC'dir; New York 08:30 yazın 12:30, kışın 13:30 UTC'dir. ABD saati
Mart'ın ikinci pazarı ileri, Kasım'ın ilk pazarı geri alır; İngiltere Mart'ın ve
Ekim'in son pazarı. Aradaki birkaç haftada Londra–New York farkı beş değil DÖRT
saattir. Bu yüzden hiçbir yerde "UTC 12:30" yazılmaz: olay (bölge, yerel saat)
çifti olarak tanımlanır ve UTC karşılığı `zoneinfo` ile gün gün çözülür.

Türkiye 2016'dan beri UTC+3'te sabittir (yaz saati yok). TSİ = UTC + 3 saat;
`tsi_sabit_mi()` bunu veri penceresinin her günü için sınar.

FX işlem günü 17:00 ET → 17:00 ET'dir: pazar 17:00 ET'de açılan seans
PAZARTESİ işlem gününe aittir. `islem_gunu()` etiketi (New York saati + 7 saat)
tarihinden kurar; böylece 17:00 ET tam gece yarısına düşer ve DST'den bağımsızdır.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

UTC = ZoneInfo("UTC")
LONDRA = ZoneInfo("Europe/London")
NEWYORK = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")
FRANKFURT = ZoneInfo("Europe/Berlin")
ISTANBUL = ZoneInfo("Europe/Istanbul")

BOLGE_ADI = {LONDRA: "Londra", NEWYORK: "New York", TOKYO: "Tokyo", FRANKFURT: "Frankfurt", ISTANBUL: "İstanbul"}

#: FX işlem gününün kapanışı (New York yerel saati).
GUN_SONU = time(17, 0)
#: Etiket kayması: 17:00 ET + 7 saat = 24:00 → ertesi gün.
_GUN_KAYMA = pd.Timedelta(hours=7)


def _saat(s: str | time) -> time:
    if isinstance(s, time):
        return s
    hh, mm = s.split(":")
    return time(int(hh), int(mm))


def yerel_an(gun: date, saat: str | time, bolge: ZoneInfo) -> datetime:
    """Bir günün yerel duvar saatini UTC ana çevirir (tek gün)."""
    t = _saat(saat)
    yerel = datetime(gun.year, gun.month, gun.day, t.hour, t.minute, tzinfo=bolge)
    # Duvar saati DST geçişinde var olmayabilir ya da iki kez geçebilir; seans
    # saatlerimiz (00:00–17:00) geçiş saatlerine (01:00–02:00) hiç denk gelmez,
    # ama denk gelirse sessizce kaydırmak yerine düşmek doğrudur.
    geri = yerel.astimezone(UTC).astimezone(bolge)
    if (geri.hour, geri.minute) != (t.hour, t.minute):
        raise ValueError(f"{gun} {t} {bolge.key}: duvar saati DST geçişine düşüyor")
    return yerel.astimezone(UTC)


def yerel_utc(gunler, saat: str | time, bolge: ZoneInfo) -> pd.DatetimeIndex:
    """Gün dizisi için yerel duvar saatinin UTC karşılıkları (vektörel)."""
    t = _saat(saat)
    g = pd.DatetimeIndex(pd.to_datetime(pd.Index(gunler)).normalize())
    if g.tz is not None:
        g = g.tz_localize(None)
    duvar = g + pd.Timedelta(hours=t.hour, minutes=t.minute)
    return duvar.tz_localize(bolge, ambiguous="raise", nonexistent="raise").tz_convert(UTC)


def islem_gunu(ts_utc) -> pd.DatetimeIndex:
    """UTC zaman damgalarının FX işlem günü etiketi (17:00 ET → 17:00 ET).

    Etiket, New York saatine 7 saat eklenmiş damganın TARİHİDİR: pazar
    17:00 ET'de açılan seans pazartesi etiketini alır, cuma 16:59 ET cuma
    etiketini alır.
    """
    ts = pd.DatetimeIndex(ts_utc)
    if ts.tz is None:
        raise ValueError("islem_gunu: damgalar UTC dilimli olmalı")
    ny = ts.tz_convert(NEWYORK).tz_localize(None)
    return (ny + _GUN_KAYMA).normalize()


def islem_gunu_sinirlari(gun: date) -> tuple[datetime, datetime]:
    """Bir işlem gününün [başlangıç, bitiş) UTC sınırları: önceki gün 17:00 ET → bugün 17:00 ET."""
    return yerel_an(gun - timedelta(days=1), GUN_SONU, NEWYORK), yerel_an(gun, GUN_SONU, NEWYORK)


def tsi(ts_utc) -> pd.DatetimeIndex:
    """UTC → TSİ (Europe/Istanbul; 2016'dan beri sabit UTC+3)."""
    return pd.DatetimeIndex(ts_utc).tz_convert(ISTANBUL)


def tsi_saat(an: datetime) -> str:
    return an.astimezone(ISTANBUL).strftime("%H:%M")


def tsi_sabit_mi(bas: date, bit: date) -> bool:
    """Penceredeki her gün için İstanbul ofseti +3 saat mi?"""
    gunler = pd.date_range(bas, bit, freq="D")
    ofs = {pd.Timestamp(g).tz_localize(ISTANBUL).utcoffset() for g in gunler}
    return ofs == {timedelta(hours=3)}


# ───────────────────────────────────────────────────────────── DST rejimleri
REJIM_ADI = {
    "kis": "Kış (ikisi de standart saat)",
    "abd_yaz_avrupa_kis": "Ara dönem (ABD yaz saatinde, Avrupa henüz değil)",
    "yaz": "Yaz (ikisi de yaz saatinde)",
    "avrupa_kis_abd_yaz": "Ara dönem (Avrupa standart saate döndü, ABD henüz değil)",
}


def _yaz_mi(gun: date, bolge: ZoneInfo) -> bool:
    # Gün ortasında bak: geçiş sabah saatlerinde olduğu için o günün çoğunu temsil eder.
    an = datetime(gun.year, gun.month, gun.day, 12, 0, tzinfo=bolge)
    return bool(an.dst())


def dst_rejimi(gun: date) -> str:
    """Günün Londra/New York yaz saati rejimi.

    Avrupa'nın yaz saati ABD'den hep SONRA başlayıp ÖNCE bittiği için
    "Londra yazda, New York kışta" bileşimi bu pencerede hiç oluşmaz; Ekim–
    Kasım ara dönemi "Londra kışta, New York yazda"dır ve ayrı adla döner.
    """
    lon, ny = _yaz_mi(gun, LONDRA), _yaz_mi(gun, NEWYORK)
    if lon and ny:
        return "yaz"
    if not lon and not ny:
        return "kis"
    if not lon and ny:
        return "abd_yaz_avrupa_kis" if gun.month <= 6 else "avrupa_kis_abd_yaz"
    # Londra yazda, New York kışta: bugünkü kurallarla oluşmaz. Oluşursa (kural
    # değişirse) sessizce bir rejime yazmak yerine düş.
    raise ValueError(f"{gun}: beklenmeyen DST bileşimi (Londra yaz, New York kış)")


def londra_ny_farki(gun: date) -> int:
    """O gün Londra ile New York arasındaki saat farkı (4 ya da 5)."""
    an = datetime(gun.year, gun.month, gun.day, 12, 0, tzinfo=UTC)
    fark = an.astimezone(LONDRA).utcoffset() - an.astimezone(NEWYORK).utcoffset()
    return int(fark.total_seconds() // 3600)


def gecisler(yil: int) -> list[tuple[date, str]]:
    """Yıl içindeki DST geçiş günleri (yerel saatin değiştiği pazarlar)."""
    sonuc = []
    for bolge, ad in ((NEWYORK, "ABD"), (LONDRA, "Avrupa")):
        onceki = None
        g = date(yil, 1, 1)
        while g.year == yil:
            d = _yaz_mi(g, bolge)
            if onceki is not None and d != onceki:
                sonuc.append((g, f"{ad} {'ileri' if d else 'geri'}"))
            onceki = d
            g += timedelta(days=1)
    return sorted(sonuc)


def ara_donemler(yil: int) -> list[tuple[date, date, str]]:
    """Londra–New York farkının 4 saat olduğu ara dönemler: [ilk gün, son gün]."""
    donem, bas, rejim = [], None, None
    g = date(yil, 1, 1)
    while g.year == yil:
        r = dst_rejimi(g)
        ara = r in ("abd_yaz_avrupa_kis", "avrupa_kis_abd_yaz")
        if ara and bas is None:
            bas, rejim = g, r
        if not ara and bas is not None:
            donem.append((bas, g - timedelta(days=1), rejim))
            bas = None
        g += timedelta(days=1)
    if bas is not None:
        donem.append((bas, date(yil, 12, 31), rejim))
    return donem


def dst_gecis_haftasi(gun: date) -> bool:
    """Gün, ABD ya da Avrupa saatinin değiştiği pazardan sonraki işlem haftasında mı?

    Saat pazar sabahı değişir; etkisi pazartesi–cuma haftasında yaşanır (seans
    saatleri bir saat kayar, alışkanlıkla emir veren katılımcı bir saat erken ya da
    geç kalabilir). Ara dönemin TAMAMI ayrı bir değişkendir (`dst_rejimi`).
    """
    for g, _ in gecisler(gun.year):
        if 0 < (gun - g).days <= 6:
            return True
    return False


# ───────────────────────────────────────────────────────────── Londra iş günü
def paskalya(yil: int) -> date:
    """Batı kilisesinin Paskalya pazarı (Gauss–Meeus–Jones–Butcher algoritması)."""
    a, b, c = yil % 19, yil // 100, yil % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    ay = (h + l - 7 * m + 114) // 31
    gun = ((h + l - 7 * m + 114) % 31) + 1
    return date(yil, ay, gun)


def _ayin_pazartesisi(yil: int, ay: int, son: bool) -> date:
    if son:
        g = date(yil + (ay == 12), ay % 12 + 1, 1) - timedelta(days=1)
        return g - timedelta(days=g.weekday())
    g = date(yil, ay, 1)
    return g + timedelta(days=(7 - g.weekday()) % 7)


#: Kuraldan sapan yıllar (İngiltere ve Galler, resmî ilanla taşınan ya da eklenen günler).
_LONDRA_OZEL = {
    2020: {"tasi": {date(2020, 5, 4): date(2020, 5, 8)}, "ek": []},              # VE Day 75. yıl
    2022: {"tasi": {date(2022, 5, 30): date(2022, 6, 2)}, "ek": [date(2022, 6, 3), date(2022, 9, 19)]},
    2023: {"tasi": {}, "ek": [date(2023, 5, 8)]},                                  # taç giyme
}


def londra_tatilleri(yil: int) -> set[date]:
    """İngiltere ve Galler resmî tatilleri (bank holidays), hafta içi günler olarak.

    Kural: yılbaşı, Paskalya'dan önceki cuma ve sonraki pazartesi, mayısın ilk ve son pazartesisi,
    ağustosun son pazartesisi, Noel ve ertesi gün; hafta sonuna düşen gün sonraki hafta içi güne
    taşınır. Kuraldan sapan yıllar `_LONDRA_OZEL`de adıyla. Kapsam bu projenin dönemidir (2018 →);
    dışında kural doğru ama özel günler girilmedi."""
    p = paskalya(yil)
    gunler = [p - timedelta(days=2), p + timedelta(days=1), _ayin_pazartesisi(yil, 5, False),
              _ayin_pazartesisi(yil, 5, True), _ayin_pazartesisi(yil, 8, True)]
    yb = date(yil, 1, 1)
    gunler.append(yb + timedelta(days={5: 2, 6: 1}.get(yb.weekday(), 0)))
    noel, ertesi = date(yil, 12, 25), date(yil, 12, 26)
    if noel.weekday() == 5:                     # cumartesi: pazartesi + salı
        gunler += [date(yil, 12, 27), date(yil, 12, 28)]
    elif noel.weekday() == 6:                   # pazar: pazartesi (ertesi) + salı
        gunler += [date(yil, 12, 26), date(yil, 12, 27)]
    elif noel.weekday() == 4:                   # cuma: ertesi gün cumartesi → pazartesi
        gunler += [noel, date(yil, 12, 28)]
    else:
        gunler += [noel, ertesi]
    ozel = _LONDRA_OZEL.get(yil, {"tasi": {}, "ek": []})
    gunler = [ozel["tasi"].get(g, g) for g in gunler] + list(ozel["ek"])
    return {g for g in gunler if g.weekday() < 5}


def londra_ay_sonu(gun: date) -> bool:
    """Gün, ayın son Londra iş günü mü (hafta içi ve İngiltere resmî tatili değil)?"""
    if gun.weekday() >= 5 or gun in londra_tatilleri(gun.year):
        return False
    g = gun + timedelta(days=1)
    while g.month == gun.month:
        if g.weekday() < 5 and g not in londra_tatilleri(g.year):
            return False
        g += timedelta(days=1)
    return True


# ───────────────────────────────────────────────────────────── olay saatleri
#: Dersin TSİ tablosunda geçen olaylar: (ad, bölge, yerel saat).
OLAYLAR = [
    ("Tokyo açılışı", TOKYO, "09:00"),
    ("Asya aralığı başlar (Londra gece yarısı)", LONDRA, "00:00"),
    ("Londra açılışı", LONDRA, "08:00"),
    ("BoE faiz kararı", LONDRA, "12:00"),
    ("New York veri saati (NFP, TÜFE)", NEWYORK, "08:30"),
    ("New York hisse açılışı", NEWYORK, "09:30"),
    ("WM/R Londra fiksingi", LONDRA, "16:00"),
    ("FOMC kararı", NEWYORK, "14:00"),
    ("FOMC basın toplantısı", NEWYORK, "14:30"),
    ("FX işlem günü kapanışı", NEWYORK, "17:00"),
]


def tsi_tablosu(gunler: list[date], olaylar=OLAYLAR) -> list[dict]:
    """Her temsilci gün için olayların TSİ saatleri (dersin tablosu)."""
    satirlar = []
    for g in gunler:
        satir = {"gun": g.isoformat(), "rejim": dst_rejimi(g), "londra_ny": londra_ny_farki(g)}
        for ad, bolge, saat in olaylar:
            satir[ad] = tsi_saat(yerel_an(g, saat, bolge))
        satirlar.append(satir)
    return satirlar


if __name__ == "__main__":
    for yil in (2025, 2026):
        print(yil, "geçişler:", [(g.isoformat(), a) for g, a in gecisler(yil)])
        print(yil, "ara dönemler:", [(b.isoformat(), s.isoformat(), r) for b, s, r in ara_donemler(yil)])
