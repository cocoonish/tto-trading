#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teknik bülten katmanlarının duman sınaması — ağsız, saniyeler içinde.

TANI DEĞİL: üretim kod yollarını sentetik veriyle sınar; düşerse koşu durmalı.
Her sigorta, korunduğu kusur GERİ KONARAK sınandı (tek yönlü sınama sigortanın
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


def _sentetik_gunluk(n: int = 400, taban: float = 100.0) -> dict[str, list]:
    zaman, acilis, yuksek, dusuk, kapanis = [], [], [], [], []
    g = dt.date(2025, 1, 6)
    i = 0
    while len(zaman) < n:
        if g.weekday() < 5:
            fiyat = taban + i * 0.05 + 3.0 * math.sin(i / 9.0)
            zaman.append(g.isoformat())
            acilis.append(fiyat - 0.2)
            yuksek.append(fiyat + 0.8)
            dusuk.append(fiyat - 0.8)
            kapanis.append(fiyat)
            i += 1
        g += dt.timedelta(days=1)
    return {"zaman": zaman, "acilis": acilis, "yuksek": yuksek,
            "dusuk": dusuk, "kapanis": kapanis}


def _sentetik_saatlik(n: int = 700, taban: float = 100.0) -> dict[str, list]:
    """Şimdiden en az 3 saat geride biten, hafta içi 24 saatlik barlar."""
    son = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)
           ).replace(minute=0, second=0, microsecond=0)
    zaman, acilis, yuksek, dusuk, kapanis = [], [], [], [], []
    t, i = son, 0
    while len(zaman) < n:
        if t.weekday() < 5:
            fiyat = taban + i * 0.01 + 1.5 * math.sin(i / 13.0)
            zaman.append(t.strftime("%Y-%m-%dT%H:%M"))
            acilis.append(fiyat - 0.05)
            yuksek.append(fiyat + 0.3)
            dusuk.append(fiyat - 0.3)
            kapanis.append(fiyat)
            i += 1
        t -= dt.timedelta(hours=1)
    for d in (zaman, acilis, yuksek, dusuk, kapanis):
        d.reverse()
    return {"zaman": zaman, "acilis": acilis, "yuksek": yuksek,
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
    s = _sentetik_gunluk()
    a = olc.atr_wilder(s["yuksek"], s["dusuk"], s["kapanis"])
    assert a and 0.5 < a < 5.0, f"ATR makul aralık dışında: {a}"
    bb = olc.bollinger(s["kapanis"])
    assert bb and bb[2] < bb[1] < bb[0], "Bollinger sırası bozuk"


def _bar_disiplini():
    bugun = dt.datetime.now(dt.timezone.utc).date().isoformat()
    t2, (k2,) = olc.kapanmis_gunler(["2026-08-25", bugun], [1.0, 2.0])
    assert bugun not in t2 and k2 == [1.0], "bugünün günlük barı düşmedi"
    # oluşmakta olan saatlik bar: başlangıç + 1 saat henüz gelmedi → düşer
    simdi = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0,
                                                     microsecond=0)
    z = [(simdi - dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
         simdi.strftime("%Y-%m-%dT%H:%M")]
    z2, (kk,) = olc.kapanmis_saatler(z, [1.0, 2.0])
    assert len(z2) == 1 and kk == [1.0], "oluşan saatlik bar düşmedi"


def _s4_kova():
    s = _sentetik_saatlik(200)
    k4 = olc.s4_kur(s["zaman"], s["acilis"], s["yuksek"], s["dusuk"],
                    s["kapanis"])
    assert k4["zaman"], "4 saatlik seri boş"
    assert set(k4["zaman"]) <= set(s["zaman"]), "4s etiketi uydurma zaman"
    simdi = dt.datetime.now(dt.timezone.utc)
    for z in k4["zaman"]:
        t = dt.datetime.fromisoformat(z).replace(tzinfo=dt.timezone.utc)
        blok_bit = t.replace(hour=(t.hour // 4) * 4, minute=0) + dt.timedelta(hours=4)
        assert blok_bit <= simdi, f"süresi dolmamış 4s kovası ölçüldü: {z}"
    # şu anki blokta tek bar → kova süresi dolmadı → düşmeli
    blok = simdi.replace(hour=(simdi.hour // 4) * 4, minute=0, second=0,
                         microsecond=0)
    tek = olc.s4_kur([blok.strftime("%Y-%m-%dT%H:%M")], [1], [1], [1], [1])
    assert not tek["zaman"], "içinde bulunulan 4s bloğu kova sayıldı"


def _haftalik_kova():
    s = _sentetik_gunluk(30)
    h = olc.haftalik_kur(s["zaman"], s["acilis"], s["yuksek"],
                         s["dusuk"], s["kapanis"])
    bugun = dt.datetime.now(dt.timezone.utc).date().isoformat()
    assert h["tarih"] and all(t < bugun for t in h["tarih"])
    assert set(h["tarih"]) <= set(s["zaman"]), "haftalık etiket uydurma tarih"


def _yapi():
    yukselen = olc.yapi_olc([(10.0, "a"), (11.0, "b"), (12.0, "c")],
                            [(8.0, "a"), (8.6, "b"), (9.4, "c")], atr=1.0)
    assert yukselen["karakter"].startswith("yükseliş"), yukselen["karakter"]
    sikisan = olc.yapi_olc([(12.0, "a"), (11.0, "b")],
                           [(8.0, "a"), (9.0, "b")], atr=1.0)
    assert sikisan["sikisma"] and sikisan["karakter"].startswith("sıkışma")
    cift = olc.yapi_olc([(12.0, "a"), (12.1, "b")],
                        [(8.0, "a"), (9.0, "b")], atr=1.0)
    assert cift["cift_tepe"] and abs(cift["cift_tepe"]["seviye"] - 12.05) < 1e-9
    ayrik = olc.yapi_olc([(12.0, "a"), (14.0, "b")],
                         [(8.0, "a"), (9.0, "b")], atr=1.0)
    assert ayrik["cift_tepe"] is None, "uzak tepeler çift tepe sayıldı"


def _olcum_ve_grafik():
    e = olc.Enstruman("SENTETIK", "sentetik", "Sentetik", "fiyat", 2)
    js, hamlar = olc.olc_enstruman(
        e, {"gunluk": _sentetik_gunluk(), "saatlik": _sentetik_saatlik()})
    for kod in ("s1", "s4", "gun"):
        d = js["dilimler"][kod]
        assert "eksik" not in d, f"{kod} dilimi eksik çıktı"
        assert d["momentum"]["rsi14"] is not None
        assert d["yapi"]["karakter"], f"{kod}: yapı karakteri boş"
        assert d["son"] is not None, f"{kod}: dilimin kendi kapanışı yok"
        for b in d["seviyeler"]["direnc"]:
            assert b["seviye"] > d["son"], f"{kod}: direnç sonun altında"
        for b in d["seviyeler"]["destek"]:
            assert b["seviye"] < d["son"], f"{kod}: destek sonun üstünde"
    assert js["haftalik"]["h10"] is not None
    eski = olc.GRAFIK
    try:
        with tempfile.TemporaryDirectory() as td:
            olc.GRAFIK = Path(td)
            for kod, ad, bar, _ in olc.DILIMLER:
                olc.ciz_dilim(e, kod, ad, hamlar[kod], bar)
            for ek in ("s1", "s4", "gunluk"):
                assert (Path(td) / f"sentetik-{ek}.html").exists(), f"{ek} grafiği yok"
    finally:
        olc.GRAFIK = eski


def _getiri_olcek():
    e = olc.Enstruman("SAHTE10Y", "s10y", "Sahte getiri", "getiri", 3, "%")
    try:
        olc.olc_enstruman(e, {"gunluk": _sentetik_gunluk(200, taban=45.0),
                              "saatlik": None})
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
                                   "seviyeler": {"destek": [{"seviye": 4.55},
                                                            {"seviye": 14641.6},
                                                            {"seviye": 14140.0}]},
                                   "yorum": None}]}
            hedef = Path(td) / "2026-08-30.json"
            hedef.write_text(json.dumps(b), encoding="utf-8")
            yama = Path(td) / "yama.json"

            def kos(icerik: dict, *ek: str) -> int:
                yama.write_text(json.dumps(icerik, ensure_ascii=False), encoding="utf-8")
                eski_argv, sys.argv = sys.argv, ["yaz.py", str(yama),
                                                 "--tarih", "2026-08-30", *ek]
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
            assert kos({"yorum": {"us10y": "hedef 14.999,9 seviyesi"}},
                       "--damgasiz") == 1, "ölçümde olmayan binlikli sayı kabul edildi"
            assert kos({"yorum": {"us10y": "14.140 tabanı ve %38,2 düzeltmesi"}},
                       "--damgasiz") == 0, \
                "sıfırla biten ölçülü sayı (14.140) ya da fib oranı reddedildi"
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
    sina("bar disiplini: bugünün günü ve oluşan saat düşer", _bar_disiplini)
    sina("4 saatlik kova: dolmamış blok yok, etiket gerçek bar", _s4_kova)
    sina("haftalık kova: kapanmamış hafta ve gelecek tarih yok", _haftalik_kova)
    sina("yapı ölçümü: yön, sıkışma, çift tepe", _yapi)
    sina("üç dilimli ölçüm + üç grafik (sentetik seri)", _olcum_ve_grafik)
    sina("getiri kotasyon ölçeği sigortası", _getiri_olcek)
    sina("yaz.py kapısı: yabancı alan/slug/sayı/damga", _yaz_kapisi)
    print(f"\n  {SAYAC['gecti']} geçti · {SAYAC['dustu']} DÜŞTÜ")
    return 1 if SAYAC["dustu"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
