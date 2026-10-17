# -*- coding: utf-8 -*-
"""Kapının (dogrula.py) ikinci tur ölçütleri, bilinen kusurlarla: kod özleri (12), pariteler (13), örnek eşiği (14),
üretilmiş metinde TSİ (15) ve MDX blok etiketi (11).

Her ölçüt arızanın kendisine karşı koşturulur: kusuru yakalayamayan bir ölçüt "temiz" der. Ölçüm dosyası geçici bir
kopyadır (ders_yaz.OLCUM yamalanır); depodaki ölçüme dokunulmaz.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

BURASI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BURASI))
import ders_yaz as dy  # noqa: E402
import dogrula as dg  # noqa: E402


def _olcum(tmp_path, monkeypatch, kunye: dict) -> Path:
    yol = tmp_path / "olcum.json"
    yol.write_text(json.dumps({"kunye": kunye}), encoding="utf-8")
    monkeypatch.setattr(dy, "OLCUM", yol)
    return yol


CIFT4 = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]


# ─────────────────────────────────────────────── 13 · pariteler
def test_parite_adi_kunyeden_ve_sayim_sozcugu(tmp_path, monkeypatch):
    _olcum(tmp_path, monkeypatch, {"ciftler": CIFT4})
    metin = tmp_path / "proje" / "metin"
    (metin / "strateji").mkdir(parents=True)
    (metin / "a.md").write_text("Kural dört paritede ölçüldü; beş majör parite yok. Adaylar en az iki paritede, "
                                "öbür üç paritede ve bu iki paritede.\n{{? x == 'altı parite' }}", encoding="utf-8")
    (metin / "strateji" / "b.md").write_text("İki paritede tutan sonuç.", encoding="utf-8")
    monkeypatch.setattr(dg, "BURASI", tmp_path / "proje")
    h = dg.parite_denetimi({"ders": ("EUR/USD ve USD/JPY yanında USD/CAD ile EUR/GBP geçiyor.", None)})
    assert any("künyede olmayan parite" in x and "EUR/GBP, USD/CAD" in x for x in h)
    sayim = [x for x in h if "parite sayısı" in x]
    assert len(sayim) == 2                        # "beş majör parite" ve "İki paritede"; nitelikli sayımlar hariç
    assert any("'beş majör parite'" in x for x in sayim) and any("'İki parite'" in x for x in sayim)
    # Künye beş parite taşısaydı "beş" doğru, "dört" yanlış olurdu: sayı künyeden.
    _olcum(tmp_path, monkeypatch, {"ciftler": CIFT4 + ["NZDUSD"]})
    sayim = [x for x in dg.parite_denetimi({}) if "parite sayısı" in x]
    assert any("'dört parite'" in x for x in sayim) and not any("'beş majör parite'" in x for x in sayim)


def test_parite_denetimi_bugunku_sablonlarda_temiz(tmp_path, monkeypatch):
    _olcum(tmp_path, monkeypatch, {"ciftler": CIFT4})
    assert [x for x in dg.parite_denetimi({}) if "parite sayısı" in x] == []


# ─────────────────────────────────────────────── 14 · örnek eşiği
def test_yarim_r_ancak_esik_yarimsa(tmp_path, monkeypatch):
    cikti = {"fade": ("Tuzak örneği önce lehine en az yarım R gidip zararla kapanır.", None)}
    _olcum(tmp_path, monkeypatch, {"ornek": {"esik": 0.5}})
    assert dg.ornek_esigi(cikti) == []
    _olcum(tmp_path, monkeypatch, {"ornek": {"esik": 0.4}})
    assert dg.ornek_esigi(cikti) and "fade" in dg.ornek_esigi(cikti)[0]
    assert dg.ornek_esigi({"fade": ("Eşik metinde geçmiyor.", None)}) == []


# ─────────────────────────────────────────────── 15 · TSİ üretilmiş metinde
MDX = """Birinci paragraf 08:30 New York'ta
(TSİ yazın 15:30, kışın 16:30) yayımlanır.

- Madde: Londra 16:00'da fiksing.
- İkinci madde Londra 16:00 (TSİ yazın 18:00, kışın 19:00).
| Kural | New York 17:00 |
# Başlık Londra 08:00
<GrafikEmbed baslik="Londra 08:00" />
Sonraki satır Londra'nın 09:00 açılışı
1. Sayılı madde: New York 14:00 – 14:30 karar penceresi

Tokyo 09:55 fiksingi (TSİ 03:55) USD/JPY'de."""


def test_tsi_metinde_paragraf_ve_madde_birimleri():
    h = dg.tsi_metinde({"x": (MDX, None)})
    satirlar = sorted(int(x.split(":")[1]) for x in h)
    # 4: TSİ'siz madde · 9: etiket satırının ardındaki satır kendi birimidir · 10: sayılı madde. Tablo, başlık ve
    # etiket satırı sınanmaz; TSİ taşıyan paragraf ve madde geçer.
    assert satirlar == [4, 9, 10]
    assert dg.tsi_metinde({"x": ("Saat yok, yalnız 3,5 R.\n\n- Madde 12:00 ama şehir yok.", None)}) == []


def test_metin_birimleri_tek_satirlik_yapilar():
    b = list(dg._metin_birimleri("# Başlık\nparagraf a\nparagraf b\n\n<div>\nmetin\n</div>\n| t |\n| u |"))
    assert b == [(1, "# Başlık"), (2, "paragraf a\nparagraf b"), (5, "<div>"), (6, "metin"), (7, "</div>"),
                 (8, "| t |"), (9, "| u |")]
    # Tablonun ardından boş satırsız gelen satır tablonun satırıdır (GFM): son satırla kalır ve sınanmaz.
    assert list(dg._metin_birimleri("| t |\nLondra 08:00 metni")) == [(1, "| t |\nLondra 08:00 metni")]


# ─────────────────────────────────────────────── 11 · MDX blok etiketi
def test_blok_etiketi_kendi_satirinda():
    assert dg.mdx_yapisi("x", "<details>\n<summary>Ç</summary>\n\nmetin\n\n</details>") == []
    assert dg.mdx_yapisi("x", "<details><summary>Çözüm</summary>\nmetin\n</details>")
    assert dg.mdx_yapisi("x", '<div class="pratik">Pratik</div>') == []      # kapanışı aynı satırda


# ─────────────────────────────────────────────── 12 · kod özleri
def _kod(tmp_path, dosya: dict, oz: str | None = None) -> dict:
    h = hashlib.sha256()
    for d, o in sorted(dosya.items()):
        h.update(f"{d}\0{o}\0".encode())
    return {"dosya": dosya, "oz": oz or h.hexdigest()}


def test_olcum_kodu_ozu_dosya_dosya(tmp_path, monkeypatch):
    proje = tmp_path / "proje"
    proje.mkdir()
    (proje / "a.py").write_text("x = 1\n")
    (proje / "b.py").write_text("y = 2\n")
    oz = {d: hashlib.sha256((proje / d).read_bytes()).hexdigest() for d in ("a.py", "b.py")}
    monkeypatch.setattr(dg, "BURASI", proje)
    monkeypatch.setattr(dg, "OLCUM_KODU_ASGARI", {"a.py"})
    _olcum(tmp_path, monkeypatch, {"kod": _kod(tmp_path, oz)})
    assert dg.olcum_kodu() == []
    (proje / "b.py").write_text("y = 3\n")                                      # kod değişti, ölçüm koşulmadı
    assert dg.olcum_kodu() == ["b.py: ölçüm koşulduktan sonra değişti (yeniden ölçülmeli)"]
    (proje / "b.py").write_text("y = 2\n")
    _olcum(tmp_path, monkeypatch, {"kod": _kod(tmp_path, {"b.py": oz["b.py"]})})    # daraltılmış liste
    assert any("asgari dosyaları taşımıyor: a.py" in x for x in dg.olcum_kodu())
    _olcum(tmp_path, monkeypatch, {"kod": _kod(tmp_path, oz, oz="0" * 64)})
    assert dg.olcum_kodu() == ["ölçümün kod özü dosya özleriyle tutmuyor"]
    _olcum(tmp_path, monkeypatch, {})
    assert "yeniden ölçülmeli" in dg.olcum_kodu()[0]


def test_olcum_kodu_ureticiyle_ayni_tanim(tmp_path, monkeypatch):
    """Üretici (ders_olcum.kod_kunyesi) ile kapı aynı öz tanımını kullanır: üreticinin yazdığı künye kapıdan geçer."""
    import ders_olcum as do
    k = do.kod_kunyesi()
    assert {"ders_olcum.py", "adlar.py"} <= set(k["dosya"]) and set(do.KOD_EK) <= set(k["dosya"])
    _olcum(tmp_path, monkeypatch, {"kod": k})
    # Sınama süreci koşuyu içe aktarmaz (kosu, strateji, strat_haber ölçüm sırasında yüklenir): asgari kapsam burada
    # sınanmaz, yalnız öz tanımı.
    monkeypatch.setattr(dg, "OLCUM_KODU_ASGARI", set())
    assert dg.olcum_kodu() == []


def test_sekil_kodu_asgari_kapsam(monkeypatch):
    oz, h = dg.sekil_kodu()
    assert h == [] and len(oz) == 64
    monkeypatch.setattr(dg, "SEKIL_KODU_ASGARI", dg.SEKIL_KODU_ASGARI | {"Aktarılacak Projeler/FxGunici/kosu.py"})
    assert "asgari dosyaları taşımıyor" in dg.sekil_kodu()[1][0]


def test_sekil_kodu_ozu_her_dosyayla_degisir(tmp_path, monkeypatch):
    import sekil_ortak as so
    a, b = tmp_path / "a.py", tmp_path / "b.py"
    a.write_text("1")
    b.write_text("2")
    monkeypatch.setattr(so, "KOK", tmp_path)
    monkeypatch.setattr(so, "SEKIL_KODU", (a, b))
    o1 = so.kod_ozu()
    b.write_text("3")
    assert so.kod_ozu() != o1
    b.write_text("2")
    assert so.kod_ozu() == o1


# ─────────────────────────────────────────────── kapının bağımlılığı
def test_kapi_agir_kutuphanesiz_kosar():
    """Yayın koşucusunda pandas, numpy, numba ve plotly yok: kapı onları istemeden içe aktarılır, figür kodunun özünü
    hesaplar ve ölçütlerini koşturur (sayfa sınavı 26 bu dosyayı orada koşturur). Hükmün kendisi (geçti ya da düştü)
    ölçümün o anki hâline bağlıdır ve burada sorulmaz; sorulan, hiçbir yolun ağır bir kütüphane istememesidir."""
    engel = ("import sys, runpy\nclass E:\n    def find_spec(self, ad, yol=None, hedef=None):\n"
             "        if ad.split('.')[0] in ('pandas', 'numpy', 'numba', 'plotly', 'pyarrow', 'scipy', 'statsmodels'):\n"
             "            raise ImportError('engellendi: ' + ad)\n"
             "sys.meta_path.insert(0, E())\n"
             f"sys.path.insert(0, {str(BURASI)!r})\n"
             "import dogrula as dg\noz, h = dg.sekil_kodu()\nassert h == [] and len(oz) == 64\n"
             "sys.argv = ['dogrula.py']\n"
             f"runpy.run_path({str(BURASI / 'dogrula.py')!r}, run_name='__main__')\n")
    r = subprocess.run([sys.executable, "-B", "-c", engel], capture_output=True, text=True, cwd=BURASI, timeout=900)
    cikti = r.stdout + r.stderr
    assert r.returncode in (0, 1) and "FX gün içi" in r.stdout, cikti[-2000:]
    for iz in ("engellendi", "No module named", "ModuleNotFoundError", "Traceback"):
        assert iz not in cikti, cikti[-2000:]
