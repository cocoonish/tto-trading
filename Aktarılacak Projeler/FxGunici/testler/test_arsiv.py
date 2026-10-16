# -*- coding: utf-8 -*-
"""Arşivleyicinin kaldığı yerden sürmesi, parça jetonları ve ertelemeli kuyruk — ağ yerine sahte kaynakla.

Birinci koşuda bazı günler kalıcı olarak geçici hata verir; arşiv o günler eksik hâlde
yazılır. İkinci koşu YALNIZ eksik günleri ister ve birimi tamamlar. Sınanan şey,
16.10.2026 bulut koşusunda iki yıllık birimin 16 ve 11 gün eksik yüzünden bütünüyle
atılmasının bir daha olmaması.
"""
from __future__ import annotations

import sys
import threading
import time
from datetime import date
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import arsiv_dukascopy as arsiv  # noqa: E402
import ayar as ay  # noqa: E402
import dukascopy as dk  # noqa: E402
from test_dukascopy import bi5, ornek_gun  # noqa: E402


def _ayar(**alan):
    a = ay.oku()
    # Hız sınırı ve erteleme sınamada saniyeler sürmesin; mantık aynı.
    taban = {"butce_dk": 5.0, "hiz_baslangic": 1000.0, "hiz_tavan": 1000.0, "ara_sn": 0.01, "tavan_deneme": 3,
             "es_zamanli": 4}
    return a.__class__(**{**a.__dict__, **taban, **alan})


def test_kaldigi_yerden_surer(tmp_path, monkeypatch):
    a = _ayar(ciftler=("EURUSD",), baslangic=date(2024, 1, 1), bitis=date(2024, 1, 10))
    monkeypatch.setattr(ay, "oku", lambda *x, **k: a)
    monkeypatch.setattr(ay, "DUKA", tmp_path / "dukascopy")
    monkeypatch.delenv("TTO_PARCA", raising=False)
    istenen: list[str] = []
    bozuk = {"2024/00/03", "2024/00/07"}
    kosu = {"n": 1}
    kilit = threading.Lock()

    def sahte_tek(url, zaman_asimi=20.0):
        with kilit:
            istenen.append(url)
        if "candles_hour" in url:
            return dk.Yanit("yok", deneme=1)
        parca = url.split("/EURUSD/")[1][:10]
        if kosu["n"] == 1 and parca in bozuk:
            return dk.Yanit("gecici", ayrinti="HTTP 503", deneme=1)
        g = int(parca[-2:])
        return dk.Yanit("tamam", bi5(ornek_gun(60, tohum=g)), deneme=1)

    monkeypatch.setattr(dk, "tek", sahte_tek)
    assert arsiv.main() == 0
    # 1–10 Ocak 2024: 6 Ocak cumartesi, istenmez → 9 gün; ikisi hatalı
    assert not [u for u in istenen if "/2024/00/06/" in u], "cumartesi istendi"
    k = dk.kunye_oku(ay.DUKA)["birimler"]["EURUSD/2024"]
    assert not k["tam"] and len(k["gun_hata"]) == 2 and k["gun_dolu"] == 7 and k["gun"] == 9
    # hatalı gün tavan_deneme (3) kez istendi, sonra bırakıldı
    assert sum(1 for u in istenen if "/2024/00/03/BID" in u) == 3
    assert k["ret"] == 4 * 3 and k["istek"] == 14 + 4 * 3
    assert sorted(p.name for p in (ay.DUKA / "kunye").glob("*.json")) == ["EURUSD_2024.json"]
    # ikinci koşu: yalnız iki eksik gün istenmeli
    kosu["n"] = 2
    istenen.clear()
    assert arsiv.main() == 0
    gunluk = [u for u in istenen if "candles_min" in u]
    assert len(gunluk) == 4 and all(any(b in u for b in bozuk) for u in gunluk)
    k = dk.kunye_oku(ay.DUKA)["birimler"]["EURUSD/2024"]
    assert k["tam"] and k["gun_dolu"] == 9 and k["satir"] == 540
    df = dk.oku_ham(ay.DUKA, "EURUSD")
    assert np.all(np.diff(df["t"].to_numpy()) > 0)
    # üçüncü koşu: tam birime dokunulmaz
    istenen.clear()
    assert arsiv.main() == 0
    assert not [u for u in istenen if "candles_min" in u]


def test_parca_jetonlari_yalniz_kendi_birimlerini_yazar(tmp_path, monkeypatch):
    a = _ayar(ciftler=("EURUSD", "GBPUSD"), baslangic=date(2023, 12, 28), bitis=date(2024, 1, 3))
    monkeypatch.setattr(ay, "oku", lambda *x, **k: a)
    monkeypatch.setattr(ay, "DUKA", tmp_path / "dukascopy")
    istenen: list[str] = []
    kilit = threading.Lock()

    def sahte_tek(url, zaman_asimi=20.0):
        with kilit:
            istenen.append(url)
        if "candles_hour" in url:
            return dk.Yanit("yok", deneme=1)
        return dk.Yanit("tamam", bi5(ornek_gun(60, tohum=1)), deneme=1)

    monkeypatch.setattr(dk, "tek", sahte_tek)
    monkeypatch.setenv("TTO_PARCA", "GBPUSD")
    assert arsiv.main() == 0
    assert istenen and all("/GBPUSD/" in u for u in istenen)
    assert sorted(p.name for p in (ay.DUKA / "kunye").glob("*.json")) == ["GBPUSD_2023.json", "GBPUSD_2024.json"]
    # tek yıl jetonu: yalnız o yılın dosyaları ve künyesi
    istenen.clear()
    monkeypatch.setenv("TTO_PARCA", "EURUSD-2024")
    assert arsiv.main() == 0
    assert istenen and all("/EURUSD/2024/" in u for u in istenen if "candles_min" in u)
    assert set(dk.kunye_oku(ay.DUKA)["birimler"]) == {"GBPUSD/2023", "GBPUSD/2024", "EURUSD/2024"}
    # aralık jetonu kalan yılı tamamlar, tam birime dokunmaz
    istenen.clear()
    monkeypatch.setenv("TTO_PARCA", "EURUSD-2023-2024")
    assert arsiv.main() == 0
    assert all("/EURUSD/2023/" in u for u in istenen if "candles_min" in u)
    assert len(dk.kunye_oku(ay.DUKA)["birimler"]) == 4
    for kotu in ("USDTRY", "eurusd", "EURUSD-2022", "EURUSD-2024-2023", "EURUSD:2024"):
        monkeypatch.setenv("TTO_PARCA", kotu)
        with pytest.raises(SystemExit):
            arsiv.main()


def test_kunye_ortak_alanlar_en_son_yazandan():
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "kunye").mkdir()
        for ad, yazim, kod in (("AUDUSD_2018", "2026-10-16T09:00:00Z", "eski"),
                               ("EURUSD_2018", "2026-10-16T10:00:00Z", "yeni")):
            s, y = ad.split("_")
            (d / "kunye" / f"{ad}.json").write_text(json.dumps(
                {"kod_ozu": kod, "yazim": yazim, "birimler": {f"{s}/{y}": {"tam": True}}}), encoding="utf-8")
        k = dk.kunye_oku(d)
        assert k["kod_ozu"] == "yeni" and set(k["birimler"]) == {"AUDUSD/2018", "EURUSD/2018"}


def test_ertelenen_dosya_sonraki_birimlerden_once_gelir(monkeypatch):
    """Süresi dolan ertelenmiş dosya, listede ondan SONRA gelen ilk denemelerin önüne geçer."""
    dk.hiz_kur(baslangic=1000.0, tavan=1000.0)
    sira: list[str] = []
    ilk_ret = {"u02"}

    def sahte_tek(url, zaman_asimi=20.0):
        time.sleep(0.02)
        sira.append(url)
        if url in ilk_ret:
            ilk_ret.discard(url)
            return dk.Yanit("gecici", ayrinti="HTTP 503", deneme=1)
        return dk.Yanit("tamam", b"x", deneme=1)

    monkeypatch.setattr(dk, "tek", sahte_tek)
    urller = [f"u{i:02d}" for i in range(15)]
    olcum: dict = {}
    y = dk.toplu_getir(urller, es_zamanli=1, ara_sn=0.03, tavan_deneme=3, olcum=olcum)
    assert all(v.durum == "tamam" for v in y.values()) and y["u02"].deneme == 2
    ikinci = [i for i, u in enumerate(sira) if u == "u02"][1]
    assert ikinci < sira.index("u14"), f"ertelenen dosya kuyruğun sonuna itildi: {sira}"
    assert olcum["deneme"]["1"] == {"tamam": 14, "gecici": 1} and olcum["deneme"]["2"] == {"tamam": 1}
    assert olcum["gecici"] == {"HTTP 503": 1} and len(olcum["sure_tamam"]) == 15


def test_butce_dolunca_denenmeyen_dosya_hata(monkeypatch):
    dk.hiz_kur(baslangic=1000.0, tavan=1000.0)
    monkeypatch.setattr(dk, "tek", lambda url, zaman_asimi=20.0: dk.Yanit("tamam", b"x", deneme=1))
    y = dk.toplu_getir(["a", "b"], son_an=time.monotonic() - 1)
    assert {v.durum for v in y.values()} == {"hata"} and all(v.deneme == 0 for v in y.values())
    # kalıcı geçici hata tavan_deneme kez denenip 'hata' olur ve son nedeni taşır
    monkeypatch.setattr(dk, "tek", lambda url, zaman_asimi=20.0: dk.Yanit("gecici", ayrinti="ReadTimeoutError"))
    y = dk.toplu_getir(["a"], es_zamanli=2, ara_sn=0.0, tavan_deneme=4)
    assert y["a"].durum == "hata" and y["a"].deneme == 4 and y["a"].ayrinti == "ReadTimeoutError"


def test_hiz_penceresi():
    h = dk.Hiz(baslangic=2.0, taban=0.5, tavan=3.0, pencere=4)
    for _ in range(4):
        h.reddedildi()
    assert abs(h.hiz - 1.5) < 1e-12 and h.sayac["ret"] == 4        # ret > %60 → %25 azalış
    for _ in range(4):
        h.basarili()
    assert abs(h.hiz - 1.725) < 1e-12                               # ret < %25 → %15 artış
    for _ in range(2):
        h.basarili()
    for _ in range(2):
        h.reddedildi(ag=True)
    assert abs(h.hiz - 1.725) < 1e-12 and h.sayac["ag"] == 2        # %50 ret: değişmez
    for _ in range(80):
        h.reddedildi()
    assert h.hiz == 0.5                                             # tabanın altına inmez
    for _ in range(200):
        h.basarili()
    assert h.hiz == 3.0                                             # tavanı aşmaz
    # 429 Retry-After herkesi birlikte bekletir
    h.reddedildi(bekle_sn=0.2)
    t = time.monotonic()
    assert h.bekle() and time.monotonic() - t >= 0.15
    # bütçe bekleme anından önce dolacaksa istek başlamaz
    h.reddedildi(bekle_sn=5.0)
    assert h.bekle(son_an=time.monotonic() + 1.0) is False
