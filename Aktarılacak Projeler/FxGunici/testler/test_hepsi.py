# -*- coding: utf-8 -*-
"""Zincirin yayın katmanı: son dört adımdan biri düşerse katman (ölçüm, figürler, dersler) zincirden önceki hâline
döner. Sınama gerçek dosyalara dokunmaz: yollar geçici dizine, adımlar küçük alt süreçlere çevrilir."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hepsi  # noqa: E402


def _kur(tmp: Path) -> tuple[Path, Path, Path]:
    dizin = tmp / "sekil"
    dizin.mkdir()
    (dizin / "a.html").write_text("eski a")
    (dizin / "b.html").write_text("eski b")
    dosya = tmp / "olcum.json"
    dosya.write_text("eski ölçüm")
    yok = tmp / "yeni-ders.mdx"          # zincirden önce yoktu
    return dizin, dosya, yok


def _durum(dizin: Path, dosya: Path, yok: Path) -> tuple:
    return (sorted((p.name, p.read_text()) for p in dizin.iterdir()), dosya.read_text(), yok.exists())


def test_yedek_her_yolu_eski_hâline_dondurur(tmp_path):
    dizin, dosya, yok = _kur(tmp_path)
    once = _durum(dizin, dosya, yok)
    y = hepsi.Yedek([dosya, dizin, yok])
    y.al()
    (dizin / "a.html").write_text("yeni a")
    (dizin / "b.html").unlink()
    (dizin / "c.html").write_text("sonradan eklenen")
    dosya.write_text("yeni ölçüm")
    yok.write_text("yeni ders")
    y.geri()
    y.sil()
    assert _durum(dizin, dosya, yok) == once


def test_yayin_adimi_duserse_katman_geri_konur(tmp_path, monkeypatch):
    dizin, dosya, yok = _kur(tmp_path)
    once = _durum(dizin, dosya, yok)
    py = sys.executable
    yaz = (f"from pathlib import Path; Path({str(dosya)!r}).write_text('yeni ölçüm'); "
           f"Path({str(dizin / 'c.html')!r}).write_text('yeni figür'); Path({str(yok)!r}).write_text('yeni ders')")
    monkeypatch.setattr(hepsi, "ADIMLAR", [
        ("önceki adım", [py, "-c", "pass"], None),
        (hepsi.YAYIN_ILK, [py, "-c", yaz], None),
        ("şekiller", [py, "-c", "import sys; sys.exit(3)"], None),
    ])
    monkeypatch.setattr(hepsi, "yayin_yollari", lambda: [dosya, dizin, yok])
    monkeypatch.setattr(hepsi, "git_on_kosulu", lambda: None)
    assert hepsi.main([]) == 3
    assert _durum(dizin, dosya, yok) == once


def test_basarili_zincir_katmani_birakir(tmp_path, monkeypatch):
    dizin, dosya, yok = _kur(tmp_path)
    py = sys.executable
    yaz = f"from pathlib import Path; Path({str(dosya)!r}).write_text('yeni ölçüm')"
    monkeypatch.setattr(hepsi, "ADIMLAR", [(hepsi.YAYIN_ILK, [py, "-c", yaz], None),
                                           ("kapı", [py, "-c", "pass"], None)])
    monkeypatch.setattr(hepsi, "yayin_yollari", lambda: [dosya, dizin, yok])
    monkeypatch.setattr(hepsi, "git_on_kosulu", lambda: None)
    assert hepsi.main([]) == 0
    assert dosya.read_text() == "yeni ölçüm"


def test_yayin_katmani_ders_sirasini_kapsar():
    import adlar
    yollar = {p.name for p in hepsi.yayin_yollari()}
    assert {f"{s}.mdx" for s in adlar.DERS_SIRA} <= yollar
    assert {"olcum.json", "fx-gunici"} <= yollar
