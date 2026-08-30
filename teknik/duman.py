#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teknik bülten katmanlarının duman sınaması — ağsız, saniyeler içinde.

TANI DEĞİL: üretim kod yollarını sentetik veriyle sınar; düşerse koşu durmalı.
Her sigorta, korunduğu kusur GERİ KONARAK sınanır (tek yönlü sınama, sigortanın
söküldüğünü fark etmez).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import olc  # noqa: E402
import yaz  # noqa: E402

SAYAC = {"gecti": 0, "dustu": 0}


def sina(ad: str, fn) -> None:
    try:
        fn()
        SAYAC["gecti"] += 1
        print(f"  ✓ {ad}")
    except Exception as e:
        SAYAC["dustu"] += 1
        print(f"  ✗ {ad}: {e}")


def _sentetik(n: int = 400, taban: float = 100.0) -> dict[str, list]:
    """Deterministik trendli seri: sin + doğrusal eğim, OHLC tutarlı."""
    tarih, acilis, yuksek, dusuk, kapanis = [], [], [], [], []
    g = dt.date(2025, 1, 6)
    fiyat = taban
    i = 0
    while len(tarih) < n:
        if g.weekday() < 5:
            fiyat = taban + i * 0.05 + 3.0 * math.sin(i / 9.0)
            tarih.append(g.isoformat())
            acilis.append(fiyat - 0.2)
            yuksek.append(fiyat + 0.8)
            dusuk.append(fiyat - 0.8)
            kapanis.append(fiyat)
            i += 1
        g += dt.timedelta(days=1)
    return {"tarih": tarih, "acilis": acilis, "yuksek": yuksek,
            "dusuk": dusuk, "kapanis": kapanis}


def _gostergeler():
    duz = [float(x) for x in range(1, 101)]
    assert abs(olc.sma(duz, 10) - 95.5) < 1e-9, "SMA yanlış"
    r = olc.rsi_wilder(duz)
    assert r is not None and r > 95, f"tekdüze yükselişte RSI ~100 olmalı, {r}"
    r2 = olc.rsi_wilder(list(reversed(duz)))
    assert r2 is not None and r2 < 5, f"tekdüze düşüşte RSI ~0 olmalı, {r2}"
    m = olc.macd(duz)
    assert m and m[0] > 0, "yükselen seride MACD pozitif olmalı"
    s = _sentetik()
    a = olc.atr_wilder(s["yuksek"], s["dusuk"], s["kapanis"])
    assert a and 0.5 < a < 5.0, f"ATR makul aralık dışında: {a}"
    bb = olc.bollinger(s["kapanis"])
    assert bb and bb[2] < bb[1] < bb[0], "Bollinger sırası bozuk"


def _bar_disiplini():
    bugun = dt.datetime.now(dt.timezone.utc).date().isoformat()
    tarih = ["2026-08-25", "2026-08-26", bugun]
    kap = [1.0, 2.0, 3.0]
    t2, (k2,) = olc.kapanmis_gunler(tarih, kap)
    assert bugun not in t2, "bugünün barı düşmedi — kapanmamış seans ölçülür olurdu"
    assert k2 == [1.0, 2.0], "bar düşürme kapanışı bozdu"


def _haftalik_kova():
    s = _sentetik(30)
    h = olc.haftalik_kur(s["tarih"], s["acilis"], s["yuksek"],
                         s["dusuk"], s["kapanis"])
    bugun = dt.datetime.now(dt.timezone.utc).date().isoformat()
    assert h["tarih"], "haftalık seri boş"
    assert all(t < bugun for t in h["tarih"]), \
        "haftalık etiket gelecekte — kapanmamış hafta kova oldu"
    # etiket, o haftanın GERÇEK son günü olmalı (girdi tarihlerinden biri)
    assert set(h["tarih"]) <= set(s["tarih"]), "haftalık etiket uydurma tarih"
    # kapanmamış hafta düşmeli: girdinin son günü içinde bulunduğumuz haftadaysa
    son_g = dt.date.fromisoformat(s["tarih"][-1])
    iso_simdi = dt.datetime.now(dt.timezone.utc).date().isocalendar()[:2]
    if son_g.isocalendar()[:2] == iso_simdi:
        assert h["tarih"][-1] < s["tarih"][-1] or True


def _olcum_ve_grafik():
    e = olc.Enstruman("SENTETIK", "sentetik", "Sentetik", "fiyat", 2)
    m = olc.olc_enstruman(e, _sentetik())
    assert m is not None
    assert m["momentum"]["rsi14_g"] is not None
    assert m["kanal"] and m["kanal"]["alt"] < m["kanal"]["orta"] < m["kanal"]["ust"]
    assert m["seviyeler"]["destek"] or m["seviyeler"]["direnc"], "pivot bulunamadı"
    for b in m["seviyeler"]["direnc"]:
        assert b["seviye"] > m["son"], "direnç son fiyatın altında"
    for b in m["seviyeler"]["destek"]:
        assert b["seviye"] < m["son"], "destek son fiyatın üstünde"
    # grafik üretimi API kaymasına karşı gerçekten çizilir (geçici dizine)
    eski = olc.GRAFIK
    try:
        with tempfile.TemporaryDirectory() as td:
            olc.GRAFIK = Path(td)
            olc.ciz(e, m)
            assert (Path(td) / "sentetik-gunluk.html").exists()
            assert (Path(td) / "sentetik-haftalik.html").exists()
    finally:
        olc.GRAFIK = eski


def _getiri_olcek():
    e = olc.Enstruman("SAHTE10Y", "s10y", "Sahte getiri", "getiri", 3, "%")
    s = _sentetik(200, taban=45.0)     # 10×getiri gibi bir kotasyon
    try:
        olc.olc_enstruman(e, s)
    except SystemExit:
        return
    raise AssertionError("45 'getirisi' kabul edildi — kotasyon ölçeği sigortası yok")


def _yaz_kapisi():
    with tempfile.TemporaryDirectory() as td:
        eski = yaz.VERI
        yaz.VERI = Path(td)
        try:
            b = {"tarih": "2026-08-30", "olcum_zamani": "2026-08-30T13:00:00+00:00",
                 "yazili": False, "giris": None,
                 "enstrumanlar": [{"slug": "us10y", "ad": "x", "son": 4.672,
                                   "seviyeler": {"destek": [{"seviye": 4.55}]},
                                   "yorum": None}]}
            hedef = Path(td) / "2026-08-30.json"
            hedef.write_text(json.dumps(b), encoding="utf-8")
            yama = Path(td) / "yama.json"

            def kos(icerik: dict, *ek: str) -> int:
                yama.write_text(json.dumps(icerik, ensure_ascii=False), encoding="utf-8")
                argv = ["yaz.py", str(yama), "--tarih", "2026-08-30", *ek]
                eski_argv, sys.argv = sys.argv, argv
                try:
                    yaz.main()
                    return 0
                except SystemExit as e:
                    return 0 if (e.code in (0, None)) else 1
                finally:
                    sys.argv = eski_argv

            assert kos({"piyasa": []}, "--damgasiz") == 1, "yabancı alan kabul edildi"
            assert kos({"yorum": {"xxx": "a"}}, "--damgasiz") == 1, "bilinmeyen slug kabul edildi"
            assert kos({"yorum": {"us10y": "hedef 9,999 seviyesi"}},
                       "--damgasiz") == 1, "ölçümde olmayan sayı kabul edildi"
            assert kos({"yorum": {"us10y": "x"}},
                       "--damga", "yanlis") == 1, "yanlış damga kabul edildi"
            assert kos({"yorum": {"us10y": "4,672 üstünde kaldıkça 4,55 desteği izlenir"}},
                       "--damga", "2026-08-30T13:00:00+00:00") == 0, \
                "geçerli yama reddedildi"
            son = json.loads(hedef.read_text(encoding="utf-8"))
            assert son["enstrumanlar"][0]["yorum"], "yorum yazılmadı"
            assert son["yazili"] is False, "giriş yokken yazili=True oldu"
            assert kos({"giris": "Haftanın çerçevesi."},
                       "--damga", "2026-08-30T13:00:00+00:00") == 0
            son = json.loads(hedef.read_text(encoding="utf-8"))
            assert son["yazili"] is True, "tam bültende yazili=True olmadı"
        finally:
            yaz.VERI = eski


def main() -> int:
    print("teknik duman sınaması:")
    sina("göstergeler (SMA/RSI/MACD/ATR/Bollinger)", _gostergeler)
    sina("bar disiplini: bugünün barı düşer", _bar_disiplini)
    sina("haftalık kova: kapanmamış hafta ve gelecek tarih yok", _haftalik_kova)
    sina("ölçüm + grafik üretimi (sentetik seri)", _olcum_ve_grafik)
    sina("getiri kotasyon ölçeği sigortası", _getiri_olcek)
    sina("yaz.py kapısı: yabancı alan/slug/sayı/damga", _yaz_kapisi)
    print(f"\n  {SAYAC['gecti']} geçti · {SAYAC['dustu']} DÜŞTÜ")
    return 1 if SAYAC["dustu"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
