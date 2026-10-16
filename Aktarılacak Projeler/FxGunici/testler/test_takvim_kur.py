# -*- coding: utf-8 -*-
"""Takvim ayrıştırıcısı: Fed'in aylık etkinlik sayfası ve FOMC basın toplantısının saat kuralı.

Fikstürler Fed sayfasının ÖLÇÜLEN biçimini taşır (16.10.2026, 103 sayfa): bölüm başlığı
`<h4 class="col-md-12">`, etkinlik başına bir `panel-body` ve üç sütun (saat · ad ve açıklama · gün).
"""
from __future__ import annotations

from datetime import date

import pytest

import takvim_kur as tk

SATIR = """
<div class="panel-body"><div class="row">
  <div class="col-xs-2"><p>{saat}</p></div>
  <div class="col-xs-7"><p>{ad}</p><p>{aciklama}</p></div>
  <div class="col-xs-3"><p>{gun}</p></div>
</div></div>"""

DUYURU = """
<div class="panel-body"><div class="row">
  <div class="col-xs-7 col-xs-offset-2"><p class="alert"><span class="icon"></span><p>{metin}</p></p></div>
  <div class="col-xs-2"><p>{gun}</p></div>
</div></div>"""


def _sayfa(*bolumler: tuple[str, str]) -> str:
    return "<html>" + "".join(f'<div class="row"><h4 class="col-md-12">{b} </h4></div>{g}' for b, g in bolumler) \
        + "</html>"


def _man(tmp_path, monkeypatch, sayfalar: dict[str, str]) -> dict:
    monkeypatch.setattr(tk, "HAM", tmp_path)
    man = {}
    for i, (u, t) in enumerate(sayfalar.items()):
        (tmp_path / f"s{i}.html").write_text(t, encoding="utf-8")
        man[u] = {"dosya": f"s{i}.html"}
    return man


def test_toplanti_satirinin_saati_basin_toplantisina_yazilmaz(tmp_path, monkeypatch):
    """2018–2025 sayfalarının biçimi: "FOMC Meeting · 2:00 p.m." ve açıklamada "Press Conference". Saat KARARINDIR."""
    s = _sayfa(("FOMC Meetings", SATIR.format(saat="2:00 p.m.", ad="FOMC Meeting",
                                              aciklama="<p>Two-day meeting, June 11-June 12<br />Press Conference</p>",
                                              gun="12")))
    man = _man(tmp_path, monkeypatch, {"https://www.federalreserve.gov/newsevents/2024-june.htm": s})
    t = tk.fed_takvim(man)
    assert [(e["saat"], e["tur"]) for e in t[date(2024, 6, 12)]] == [("14:00", "toplanti")]


def test_ayri_basin_satiri_ve_duyuru_gunu(tmp_path, monkeypatch):
    """Ayrı satır (Eylül 2025'ten itibaren) "basin"; duyurunun günü yayım günüdür, metnin adını verdiği gün de anahtar."""
    s = _sayfa(
        ("Announcements", DUYURU.format(
            gun="27", metin="Federal government offices are closed Tuesday, January 27. The Federal Open Market "
                            "Committee will meet as planned on Tuesday, January 27 and Wednesday, January 28. The "
                            "FOMC statement will be released as scheduled at 2 p.m. EST, and the Chair's news "
                            "conference will start at 2:30 p.m. EST.")),
        ("Speeches", SATIR.format(saat="2:30 p.m.", ad="FOMC Press Conference", aciklama="", gun="5")),
        ("FOMC Meetings", SATIR.format(saat="2:30 p.m.", ad='<a href="/live-broadcast.htm">FOMC Press Conference</a>',
                                       aciklama="", gun="28")),
    )
    man = _man(tmp_path, monkeypatch, {"https://www.federalreserve.gov/newsevents/2026-january.htm": s})
    t = tk.fed_takvim(man)
    assert sorted((e["saat"], e["tur"]) for e in t[date(2026, 1, 28)]) == [("14:30", "basin"), ("14:30", "duyuru")]
    assert [e["tur"] for e in t[date(2026, 1, 27)]] == ["duyuru"]
    assert date(2026, 1, 5) not in t, "FOMC bölümü dışındaki satır FOMC etkinliği sayılmaz"
    assert [e["dilim"] for e in t[date(2026, 1, 28)] if e["tur"] == "duyuru"] == ["EST"]


KURAL = ("<p>For release at 4:00 p.m. EDT</p><p>Committee policy statements for all regularly scheduled meetings will "
         "now be released at 2 p.m. Eastern Time. For meetings with news conferences, the Committee's current economic "
         "projections will also be released at 2 p.m. Eastern Time, and the Chairman's news conference will begin at "
         "approximately 2:30 p.m. Eastern Time.</p>")


def test_kural_ve_celisen_yineleme(tmp_path, monkeypatch):
    yineleme = "<p>the Chair holds a news conference at 3:00 p.m. Eastern Time the same day.</p>"
    sadik = "<p>the Chair holds a news conference at 2:30 p.m. Eastern Time the same day.</p>"
    karar_cumlesi = "<p>a press conference following the 2:00 p.m. statement.</p>"   # yineleme sayılmaz
    man = _man(tmp_path, monkeypatch, {
        tk.FED_KURAL: KURAL,
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20240809a.htm": sadik,
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20250905a.htm": karar_cumlesi,
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20300101a.htm": yineleme,
    })
    k = tk.fomc_kurali(man)
    assert (k["karar"], k["basin"]) == ("14:00", "14:30")
    assert [(y["tarih"], y["saat"]) for y in k["yineleme"]] == [("2024-08-09", "14:30"), ("2030-01-01", "15:00")]
    assert k["son_gecerli"] == "2030-01-01"


def test_kural_olagan_toplantiya_ve_kural_saatindeki_karara_uygulanir(tmp_path, monkeypatch):
    """Olağanüstü toplantının kararı kuralın saatinde (14:00) yayımlansa bile basın toplantısı kuraldan yazılmaz;
    olağan toplantının kararı başka saatte yayımlandıysa da yazılmaz (kuralın eşi tutmuyor)."""
    takvim = ('<h5 class="panel-heading">March 2 (unscheduled) Meeting - 2020</h5>'
              '<a href="/newsevents/pressreleases/monetary20200302a.htm">Statement</a>'
              '<a href="/monetarypolicy/fomcpresconf20200302.htm">Press Conference</a>'
              '<h5 class="panel-heading">April 28-29 Meeting - 2020</h5>'
              '<a href="/newsevents/pressreleases/monetary20200429a.htm">Statement</a>'
              '<a href="/monetarypolicy/fomcpresconf20200429.htm">Press Conference</a>'
              '<h5 class="panel-heading">June 9-10 Meeting - 2020</h5>'
              '<a href="/newsevents/pressreleases/monetary20200610a.htm">Statement</a>'
              '<a href="/monetarypolicy/fomcpresconf20200610.htm">Press Conference</a>')
    kok = "https://www.federalreserve.gov/newsevents/pressreleases/"
    man = _man(tmp_path, monkeypatch, {
        tk.FED_KURAL: KURAL,
        "https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm": takvim,
        kok + "monetary20200302a.htm": "<p>For release at 2:00 p.m. EST</p>",
        kok + "monetary20200429a.htm": "<p>For release at 2:00 p.m. EDT</p>",
        kok + "monetary20200610a.htm": "<p>For release at 12:30 p.m. EDT</p>",
    })
    kunye: dict = {}
    satir = tk.fomc(man, kunye)
    assert sorted(s["tarih"] for s in satir if s["olay"] == "FOMC_karar") == ["2020-03-02", "2020-04-29",
                                                                               "2020-06-10"]
    basin = [(s["tarih"], s["yerel_saat"]) for s in satir if s["olay"] == "FOMC_basin"]
    assert basin == [("2020-04-29", "14:30")]
    assert any("2020-03-02: olağanüstü" in s for s in kunye["fomc"]["sorun"])
    assert any("2020-06-10: karar 12:30" in s for s in kunye["fomc"]["sorun"])


def test_kural_yoksa_kurulmaz(tmp_path, monkeypatch):
    man = _man(tmp_path, monkeypatch, {tk.FED_KURAL: "<p>Bu duyurunun metni değişmiş.</p>"})
    k = tk.fomc_kurali(man)
    assert k["basin"] is None and k["sorun"]


@pytest.mark.skipif(not (tk.HAM / "manifest5_fed-kural.json").exists(), reason="beşinci arşiv geçişi koşmadı")
def test_arsivdeki_takvim():
    """Depodaki dondurulmuş arşiv: kural 14:00 / 14:30; her basın toplantısı kendi kararından 30 dakika sonra;
    olağanüstü toplantının basın toplantısı kuraldan yazılmaz."""
    man = tk._manifest()
    kunye: dict = {}
    satir = tk.fomc(man, kunye)
    karar = {s["tarih"]: s for s in satir if s["olay"] == "FOMC_karar"}
    basin = [s for s in satir if s["olay"] == "FOMC_basin"]
    assert (kunye["fomc"]["kural"]["karar"], kunye["fomc"]["kural"]["basin"]) == ("14:00", "14:30")
    assert basin, "basın toplantısı yazılmadı"
    for b in basin:
        k = karar[b["tarih"]]
        sa, dk = map(int, k["yerel_saat"].split(":"))
        assert b["yerel_saat"] == f"{sa:02d}:{dk + 30:02d}", b
    for k in karar.values():
        if k["not"] == "olağanüstü toplantı":
            assert not any(b["tarih"] == k["tarih"] and "kuralından" in b["not"] for b in basin), k
    # Tarih tarih kaynağı olan basın toplantıları (aylık takvimin ayrı satırı ya da duyurusu) kuralla aynı saatte.
    assert kunye["fomc"]["basin_saat_kaynagi"]["takvim"] + kunye["fomc"]["basin_saat_kaynagi"]["duyuru"] >= 1
    assert not [s for s in kunye["fomc"]["sorun"] if "takvim" in s and "kural" in s and "diyor" in s]
