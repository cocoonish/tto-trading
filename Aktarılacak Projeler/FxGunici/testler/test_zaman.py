# -*- coding: utf-8 -*-
"""Zaman katmanının birim testleri.

Kullanıcının koyduğu şartlar: Londra açılışı yazın 10:00, kışın 11:00 TSİ;
08:30 ET yazın 15:30, kışın 16:30 TSİ; geçiş haftaları da doğru yakalanmalı.
Geçiş tarihleri ELLE yazıldı (resmî kural: ABD Mart'ın ikinci pazarı / Kasım'ın
ilk pazarı, İngiltere Mart'ın ve Ekim'in son pazarı) — `zoneinfo`ya karşı
bağımsız bir kıyas olsun diye; kodun kendi çıktısından türetilmedi.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import zaman as z  # noqa: E402

# (yıl, ABD ileri, Avrupa ileri, Avrupa geri, ABD geri) — elle.
GECISLER = [
    (2018, date(2018, 3, 11), date(2018, 3, 25), date(2018, 10, 28), date(2018, 11, 4)),
    (2019, date(2019, 3, 10), date(2019, 3, 31), date(2019, 10, 27), date(2019, 11, 3)),
    (2020, date(2020, 3, 8), date(2020, 3, 29), date(2020, 10, 25), date(2020, 11, 1)),
    (2021, date(2021, 3, 14), date(2021, 3, 28), date(2021, 10, 31), date(2021, 11, 7)),
    (2022, date(2022, 3, 13), date(2022, 3, 27), date(2022, 10, 30), date(2022, 11, 6)),
    (2023, date(2023, 3, 12), date(2023, 3, 26), date(2023, 10, 29), date(2023, 11, 5)),
    (2024, date(2024, 3, 10), date(2024, 3, 31), date(2024, 10, 27), date(2024, 11, 3)),
    (2025, date(2025, 3, 9), date(2025, 3, 30), date(2025, 10, 26), date(2025, 11, 2)),
    (2026, date(2026, 3, 8), date(2026, 3, 29), date(2026, 10, 25), date(2026, 11, 1)),
]


def tsi(gun: date, saat: str, bolge) -> str:
    return z.tsi_saat(z.yerel_an(gun, saat, bolge))


# ───────────────────────────────────────── kullanıcının açık şartları
def test_londra_acilisi_yaz_10_kis_11():
    assert tsi(date(2026, 7, 15), "08:00", z.LONDRA) == "10:00"
    assert tsi(date(2026, 1, 15), "08:00", z.LONDRA) == "11:00"


def test_ny_0830_yaz_1530_kis_1630():
    assert tsi(date(2026, 7, 15), "08:30", z.NEWYORK) == "15:30"
    assert tsi(date(2026, 1, 15), "08:30", z.NEWYORK) == "16:30"


@pytest.mark.parametrize("yil,abd_ileri,avr_ileri,avr_geri,abd_geri", GECISLER)
def test_gecis_gunleri_elle_yazilanla_ayni(yil, abd_ileri, avr_ileri, avr_geri, abd_geri):
    beklenen = sorted([
        (abd_ileri, "ABD ileri"), (avr_ileri, "Avrupa ileri"),
        (avr_geri, "Avrupa geri"), (abd_geri, "ABD geri"),
    ])
    assert z.gecisler(yil) == beklenen
    for g in (abd_ileri, avr_ileri, avr_geri, abd_geri):
        assert g.weekday() == 6, f"{g} pazar değil"


@pytest.mark.parametrize("yil,abd_ileri,avr_ileri,avr_geri,abd_geri", GECISLER)
def test_gecis_haftalari_tsi(yil, abd_ileri, avr_ileri, avr_geri, abd_geri):
    """Her geçişin iki yakasında Londra 08:00 ve New York 08:30'un TSİ karşılığı."""
    gun = lambda g, n: g + timedelta(days=n)  # noqa: E731
    # Mart ara dönemi: ABD yazda, Londra kışta → Londra 11:00, New York 15:30.
    assert tsi(gun(abd_ileri, -2), "08:30", z.NEWYORK) == "16:30"   # önceki cuma
    assert tsi(gun(abd_ileri, 1), "08:30", z.NEWYORK) == "15:30"    # ertesi pazartesi
    assert tsi(gun(abd_ileri, 1), "08:00", z.LONDRA) == "11:00"
    assert tsi(gun(avr_ileri, -2), "08:00", z.LONDRA) == "11:00"
    assert tsi(gun(avr_ileri, -2), "08:30", z.NEWYORK) == "15:30"
    assert tsi(gun(avr_ileri, 1), "08:00", z.LONDRA) == "10:00"     # yaz
    assert tsi(gun(avr_ileri, 1), "08:30", z.NEWYORK) == "15:30"
    # Ekim–Kasım ara dönemi: Londra kışa döndü, ABD hâlâ yazda.
    assert tsi(gun(avr_geri, -2), "08:00", z.LONDRA) == "10:00"
    assert tsi(gun(avr_geri, 1), "08:00", z.LONDRA) == "11:00"
    assert tsi(gun(avr_geri, 1), "08:30", z.NEWYORK) == "15:30"
    assert tsi(gun(abd_geri, -2), "08:30", z.NEWYORK) == "15:30"
    assert tsi(gun(abd_geri, 1), "08:30", z.NEWYORK) == "16:30"     # kış
    assert tsi(gun(abd_geri, 1), "08:00", z.LONDRA) == "11:00"


@pytest.mark.parametrize("yil,abd_ileri,avr_ileri,avr_geri,abd_geri", GECISLER)
def test_ara_donemler_ve_londra_ny_farki(yil, abd_ileri, avr_ileri, avr_geri, abd_geri):
    assert z.ara_donemler(yil) == [
        (abd_ileri, avr_ileri - timedelta(days=1), "abd_yaz_avrupa_kis"),
        (avr_geri, abd_geri - timedelta(days=1), "avrupa_kis_abd_yaz"),
    ]
    assert z.londra_ny_farki(abd_ileri + timedelta(days=1)) == 4
    assert z.londra_ny_farki(avr_geri + timedelta(days=1)) == 4
    assert z.londra_ny_farki(date(yil, 7, 1)) == 5
    assert z.londra_ny_farki(date(yil, 1, 15)) == 5


def test_dst_gecis_haftasi():
    assert z.dst_gecis_haftasi(date(2026, 3, 9))       # ABD geçişinden sonraki pazartesi
    assert z.dst_gecis_haftasi(date(2026, 3, 13))      # aynı haftanın cuması
    assert not z.dst_gecis_haftasi(date(2026, 3, 16))  # bir sonraki hafta (ara dönem ama geçiş haftası değil)
    assert z.dst_rejimi(date(2026, 3, 16)) == "abd_yaz_avrupa_kis"
    assert z.dst_gecis_haftasi(date(2026, 10, 26))
    assert z.dst_gecis_haftasi(date(2026, 11, 2))


# ───────────────────────────────────────── FX işlem günü
def _utc(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")


def test_islem_gunu_kis_ve_yaz():
    # Kış: 17:00 EST = 22:00 UTC.
    assert z.islem_gunu([_utc("2026-01-16 21:59")])[0] == pd.Timestamp("2026-01-16")  # cuma 16:59 ET
    assert z.islem_gunu([_utc("2026-01-18 22:00")])[0] == pd.Timestamp("2026-01-19")  # pazar 17:00 ET → pazartesi
    # Yaz: 17:00 EDT = 21:00 UTC.
    assert z.islem_gunu([_utc("2026-07-14 20:59")])[0] == pd.Timestamp("2026-07-14")
    assert z.islem_gunu([_utc("2026-07-14 21:00")])[0] == pd.Timestamp("2026-07-15")


def test_islem_gunu_dst_geciş_pazari():
    # 08.03.2026 pazar: ABD saati sabah ileri alındı; akşam 17:00 EDT = 21:00 UTC.
    assert z.islem_gunu([_utc("2026-03-08 20:59")])[0] == pd.Timestamp("2026-03-08")
    assert z.islem_gunu([_utc("2026-03-08 21:00")])[0] == pd.Timestamp("2026-03-09")
    bas, bit = z.islem_gunu_sinirlari(date(2026, 3, 9))
    assert bas == datetime(2026, 3, 8, 21, 0, tzinfo=z.UTC)
    assert bit == datetime(2026, 3, 9, 21, 0, tzinfo=z.UTC)
    # Önceki cuma hâlâ kış saatinde kapandı: 17:00 EST = 22:00 UTC.
    bas, bit = z.islem_gunu_sinirlari(date(2026, 3, 6))
    assert bit == datetime(2026, 3, 6, 22, 0, tzinfo=z.UTC)


def test_islem_gunu_dilimsiz_damgayi_reddeder():
    with pytest.raises(ValueError):
        z.islem_gunu(pd.DatetimeIndex(["2026-01-16 21:59"]))


# ───────────────────────────────────────── vektörel ↔ tekil, TSİ sabitliği
@pytest.mark.parametrize("saat,bolge", [("08:00", z.LONDRA), ("08:30", z.NEWYORK), ("00:00", z.LONDRA),
                                        ("09:00", z.TOKYO), ("16:00", z.LONDRA), ("14:30", z.NEWYORK),
                                        ("17:00", z.NEWYORK)])
def test_vektorel_tekil_ile_ayni(saat, bolge):
    gunler = pd.date_range("2018-01-01", "2026-12-31", freq="D")
    vek = z.yerel_utc(gunler, saat, bolge)
    tek = pd.DatetimeIndex([z.yerel_an(g.date(), saat, bolge) for g in gunler]).tz_convert("UTC")
    assert (vek == tek).all()


def test_tsi_her_gun_utc_arti_uc():
    assert z.tsi_sabit_mi(date(2018, 1, 1), date(2026, 12, 31))


def test_dst_gecisine_dusen_duvar_saati_duser():
    with pytest.raises(ValueError):
        z.yerel_an(date(2026, 3, 8), "02:30", z.NEWYORK)   # 02:00 → 03:00 atlandı
    with pytest.raises(ValueError):
        z.yerel_utc([date(2026, 3, 8)], "02:30", z.NEWYORK)


def test_tsi_tablosu_temsilci_gunler():
    t = {r["gun"]: r for r in z.tsi_tablosu([date(2026, 1, 15), date(2026, 3, 16), date(2026, 7, 15), date(2026, 10, 28)])}
    assert t["2026-01-15"]["Londra açılışı"] == "11:00" and t["2026-01-15"]["New York veri saati (NFP, TÜFE)"] == "16:30"
    assert t["2026-03-16"]["Londra açılışı"] == "11:00" and t["2026-03-16"]["New York veri saati (NFP, TÜFE)"] == "15:30"
    assert t["2026-07-15"]["Londra açılışı"] == "10:00" and t["2026-07-15"]["New York veri saati (NFP, TÜFE)"] == "15:30"
    assert t["2026-10-28"]["Londra açılışı"] == "11:00" and t["2026-10-28"]["New York veri saati (NFP, TÜFE)"] == "15:30"
    assert t["2026-07-15"]["FX işlem günü kapanışı"] == "00:00"
    assert t["2026-01-15"]["FX işlem günü kapanışı"] == "01:00"
    assert t["2026-07-15"]["Tokyo açılışı"] == "03:00"


# ───────────────────────────────────────────── Londra iş günü (ay sonu, ön kayıt [fiks])
# İngiltere ve Galler resmî tatilleri ELLE (yalnız hafta içi; resmî listeyle ayrıca aşağıda): kodun kendi
# kuralından türetilmedi. Özel yıllar dahil: 2020 VE Day cumaya taşındı, 2022 Jübile ve cenaze,
# 2023 taç giyme.
LONDRA_ELLE = {
    2018: ["01-01", "03-30", "04-02", "05-07", "05-28", "08-27", "12-25", "12-26"],
    2019: ["01-01", "04-19", "04-22", "05-06", "05-27", "08-26", "12-25", "12-26"],
    2020: ["01-01", "04-10", "04-13", "05-08", "05-25", "08-31", "12-25", "12-28"],
    2021: ["01-01", "04-02", "04-05", "05-03", "05-31", "08-30", "12-27", "12-28"],
    2022: ["01-03", "04-15", "04-18", "05-02", "06-02", "06-03", "08-29", "09-19", "12-26", "12-27"],
    2023: ["01-02", "04-07", "04-10", "05-01", "05-08", "05-29", "08-28", "12-25", "12-26"],
    2024: ["01-01", "03-29", "04-01", "05-06", "05-27", "08-26", "12-25", "12-26"],
    2025: ["01-01", "04-18", "04-21", "05-05", "05-26", "08-25", "12-25", "12-26"],
    2026: ["01-01", "04-03", "04-06", "05-04", "05-25", "08-31", "12-25", "12-28"],
}


@pytest.mark.parametrize("yil", sorted(LONDRA_ELLE))
def test_londra_tatilleri_elle_yazilanla_ayni(yil):
    beklenen = {date(yil, int(g[:2]), int(g[3:])) for g in LONDRA_ELLE[yil]}
    assert z.londra_tatilleri(yil) == beklenen


def test_paskalya():
    assert z.paskalya(2024) == date(2024, 3, 31)
    assert z.paskalya(2026) == date(2026, 4, 5)
    assert z.paskalya(2019) == date(2019, 4, 21)


def test_londra_ay_sonu_tatile_dusen_son_gun():
    # Ayın son hafta içi günü Londra tatili: ay sonu bir önceki iş günü.
    assert not z.londra_ay_sonu(date(2024, 3, 29)) and z.londra_ay_sonu(date(2024, 3, 28))
    assert not z.londra_ay_sonu(date(2026, 8, 31)) and z.londra_ay_sonu(date(2026, 8, 28))
    assert not z.londra_ay_sonu(date(2021, 5, 31)) and z.londra_ay_sonu(date(2021, 5, 28))
    assert not z.londra_ay_sonu(date(2020, 8, 31)) and z.londra_ay_sonu(date(2020, 8, 28))
    assert not z.londra_ay_sonu(date(2018, 3, 30)) and z.londra_ay_sonu(date(2018, 3, 29))
    # Sıradan ay: son hafta içi gün; hafta sonu hiçbir zaman ay sonu değil.
    assert z.londra_ay_sonu(date(2026, 9, 30)) and not z.londra_ay_sonu(date(2026, 9, 29))
    assert z.londra_ay_sonu(date(2026, 10, 30)) and not z.londra_ay_sonu(date(2026, 10, 31))
    # Her ayın tam olarak bir ay sonu günü var (2018–2026).
    for y in range(2018, 2027):
        for a in range(1, 13):
            g, say = date(y, a, 1), 0
            while g.month == a:
                say += z.londra_ay_sonu(g)
                g += timedelta(days=1)
            assert say == 1, (y, a)


def test_londra_tatilleri_resmi_listeyle_ayni():
    """Resmî liste (gov.uk, bulut koşusunda indirilir) varsa kural onun KAPSADIĞI her yılda birebir
    aynı olmalı. Liste yoksa sınama atlanır ve adıyla söylenir: koşmamış bir kıyas geçmiş sayılmaz."""
    import json
    yol = Path(__file__).resolve().parents[1] / "veri" / "takvim" / "ham" / "londra_tatil.json"
    if not yol.exists():
        pytest.skip("resmî liste henüz indirilmedi (arsiv_takvim4, parça londra-tatil)")
    d = json.loads(yol.read_text(encoding="utf-8"))
    yillar: dict[int, set] = {}
    for kaynak in d.values():
        for e in kaynak.get("olay") or []:
            g = date.fromisoformat(e["date"])
            yillar.setdefault(g.year, set()).add(g)
    tam = [y for y, gs in yillar.items() if any(g.month == 1 for g in gs) and any(g.month == 12 for g in gs)]
    assert tam, "resmî listede tam yıl yok"
    for y in tam:
        if 2018 <= y <= 2026:
            assert z.londra_tatilleri(y) == {g for g in yillar[y] if g.weekday() < 5}, y
