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
                                "öbür üç paritede ve bu iki paritede; seçim en az\niki paritede tuttu.\n"
                                "{{? x == 'altı parite' }}", encoding="utf-8")
    (metin / "strateji" / "b.md").write_text("İki paritede tutan sonuç. Yalnız üç majör (EUR/USD, GBP/USD); çapraz "
                                             "kurlar yok.", encoding="utf-8")
    monkeypatch.setattr(dg, "BURASI", tmp_path / "proje")
    h = dg.parite_denetimi({"ders": ("EUR/USD ve USD/JPY yanında USD/CAD ile EUR/GBP geçiyor.", None)})
    assert any("künyede olmayan parite" in x and "EUR/GBP, USD/CAD" in x for x in h)
    sayim = [x for x in h if "parite sayısı" in x]
    assert len(sayim) == 3          # "beş majör parite", "İki paritede", "üç majör (…)"; nitelikli sayımlar hariç
    assert any("'beş majör parite'" in x for x in sayim) and any("'İki parite'" in x for x in sayim)
    assert any("'üç majör'" in x for x in sayim)  # "parite" sözcüğü olmadan, parantezli listeyle verilen sayı
    # Künye beş parite taşısaydı "beş" doğru, "dört" yanlış olurdu: sayı künyeden.
    _olcum(tmp_path, monkeypatch, {"ciftler": CIFT4 + ["NZDUSD"]})
    sayim = [x for x in dg.parite_denetimi({}) if "parite sayısı" in x]
    assert any("'dört parite'" in x for x in sayim) and not any("'beş majör parite'" in x for x in sayim)


def test_parite_denetimi_bugunku_sablonlarda_temiz(tmp_path, monkeypatch):
    _olcum(tmp_path, monkeypatch, {"ciftler": CIFT4})
    assert [x for x in dg.parite_denetimi({}) if "parite sayısı" in x] == []


# ─────────────────────────────────────────────── 16 · kural sabitleri (ATR periyodu)
ATR_KUNYE = {"atr_kural": 14, "haber_sabit": {"atr_mum": 14, "atr_gun": 14}}


def test_atr_yazimi_on_kayittan(tmp_path, monkeypatch):
    _olcum(tmp_path, monkeypatch, ATR_KUNYE)
    h = dg.atr_denetimi({"d": ("R girişteki ATR(14); stop 0,5 × ATR(20) içi.", None)})
    assert len(h) == 1 and "ATR(20)" in h[0]
    d = {"layout": {"title": {"text": "R birimi girişteki ATR(21)"}, "annotations": [{"text": "ATR(14)"}]}}
    assert [x for x in dg.atr_figurde("f", d) if "ATR(21)" in x] and len(dg.atr_figurde("f", d)) == 1
    # Ön kayıt periyotlarından biri 14 kaldıkça "ATR(14)" geçer; üçü de 20'ye çekilseydi bugünkü "ATR(14)"
    # yazımları düşerdi: sayı künyeden.
    _olcum(tmp_path, monkeypatch, {**ATR_KUNYE, "atr_kural": 20})
    assert dg.atr_denetimi({"d": ("ATR(14) ve ATR(20)", None)}) == []
    _olcum(tmp_path, monkeypatch, {"atr_kural": 20, "haber_sabit": {"atr_mum": 20, "atr_gun": 20}})
    assert any("ATR(14)" in x for x in dg.atr_denetimi({"d": ("ATR(14)", None)}))
    # Künye periyodu taşımıyorsa kapı "temiz" demez.
    _olcum(tmp_path, monkeypatch, {})
    assert any("künyede ATR periyodu yok" in x for x in dg.atr_denetimi({"d": ("ATR(14)", None)}))


def test_kural_kodundaki_atr_on_kayitla_ayni():
    # Metnin dayandığı künye sayısı ön kayıttan; kural kodu periyodu ayrıca yazıyor (strateji.py, gunluk.py). İkisi
    # ayrışırsa metin ön kayda uyar ama kod başka bir ATR'yle koşmuş olur.
    import re
    import tomllib
    onk = tomllib.loads((BURASI / "onkayit.toml").read_text(encoding="utf-8"))
    kural = {int(x) for x in re.findall(r"atr_mum\(\w+,\s*(\d+)\)", (BURASI / "strateji.py").read_text(encoding="utf-8"))}
    assert kural == {int(onk["genel"]["atr_mum"])}
    gun = re.search(r"^ATR_GUN = (\d+)", (BURASI / "gunluk.py").read_text(encoding="utf-8"), re.M)
    assert gun and int(gun.group(1)) == int(onk["genel"]["gun_atr"])


# ─────────────────────────────────────────────── 14 · örnek eşiği
def test_yarim_r_ancak_esik_yarimsa(tmp_path, monkeypatch):
    cikti = {"fade": ("Tuzak örneği önce lehine en az yarım R gidip zararla kapanır.", None)}
    _olcum(tmp_path, monkeypatch, {"ornek": {"esik": 0.5}})
    assert dg.ornek_esigi(cikti) == []
    _olcum(tmp_path, monkeypatch, {"ornek": {"esik": 0.4}})
    assert dg.ornek_esigi(cikti) and "fade" in dg.ornek_esigi(cikti)[0]
    assert dg.ornek_esigi({"fade": ("Eşik metinde geçmiyor.", None)}) == []


# ─────────────────────────────────────────────── 15 · TSİ üretilmiş metinde
def _neden(b: str, **kw) -> list[str]:
    return [n for _, n in dg.tsi_saatleri(b, **kw)]


def test_tsi_saat_basina_degerleri_sorar():
    # Yerel saatin bütün rejim karşılıkları aynı cümlede TSİ olarak durmalı; "TSİ" sözcüğünün varlığı yetmez.
    assert _neden("Fiksing Londra 16:00'da (TSİ İngiltere yaz saatinde 18:00, kış saatinde 19:00).") == []
    assert _neden("Fiksing Londra 16:00'da (TSİ 18:00).") == ["Londra 16:00 → TSİ 18:00 · 19:00 yazılı değil"]
    assert _neden("Fiksing Londra 16:00'da.") == ["Londra 16:00 → TSİ 18:00 · 19:00 yazılı değil"]
    # Tokyo saat değiştirmez: tek değer.
    assert _neden("Tokyo 09:55 fiksingi (TSİ 03:55) USD/JPY'de.") == []
    # Şehri hiçbir yerden okunamayan saat adıyla düşer.
    assert _neden("Madde 12:00 ama şehir yok.") == ["şehri belirsiz"]


def test_tsi_sehir_bitisik_aralik_ve_satir_sonu():
    # Şehir saatin önünde ya da ardında; aralığın iki ucu aynı şehrindir; MDX satır sonunu boşluk basar.
    assert _neden("Karar 14:00 New York (TSİ ABD yaz saatinde 21:00, kış saatinde 22:00).") == []
    h = _neden("Karar penceresi New York 14:00 – 14:30.")
    assert h == ["New York 14:00 → TSİ 21:00 · 22:00 yazılı değil", "New York 14:30 → TSİ 21:30 · 22:30 yazılı değil"]
    assert _neden("Veri New\nYork 08:30'da gelir.") == ["New York 08:30 → TSİ 15:30 · 16:30 yazılı değil"]
    # Şehri cümlede geçen TEK şehirden okunan saat.
    assert _neden("Londra açılışından sonra 09:00'da (TSİ İngiltere yaz saatinde 11:00, kış saatinde 12:00).") == []


def test_tsi_tarihli_saat_o_gunun_karsiligi():
    # Tarih saatin hemen önündeyse karşılık yalnız o günündür (15.03.2026: ABD yaz, İngiltere kış saatinde).
    assert _neden("15.03.2026 14:00 New York kararı (TSİ 21:00).") == []
    assert _neden("15 Mart 2026 14:00 New York kararı (TSİ 21:00).") == []
    assert _neden("Mart ortasında 14:00 New York kararı (TSİ 21:00).") == \
        ["New York 14:00 → TSİ 21:00 · 22:00 yazılı değil"]


def test_tsi_rejim_niteligi_en_yakini_ve_tsi_yaziminda_aranmaz():
    # Saatin rejimi adıyla söylenmişse yalnız o rejimin karşılığı istenir; birden çok niteleyiciden saate en yakını.
    assert _neden("Pencere yazın kapanır; kışın Londra 16:00 fiksingi (TSİ 19:00).") == []
    assert _neden("Pencere kışın kapanır; yazın Londra 16:00 fiksingi (TSİ 19:00).") == \
        ["Londra 16:00 → TSİ 18:00 yazılı değil"]
    assert dg._rejim_niteligi("yazın … kışın", son=True) == "kis"
    assert dg._rejim_niteligi("yazın … kışın") == "yaz"
    # TSİ'nin kendi yazımındaki rejim sözcüğü başka bir yerel saatin niteleyicisi değildir: maskelenmese Londra
    # 14:30 "yazın" sayılır, karşılığı (16:30) TSİ parantezinde tesadüfen bulunur ve eksik kış değeri (17:30) görünmezdi.
    assert _neden("Veri New York 08:30'da (TSİ kışın 16:30, yazın 15:30), Londra 14:30'da açılır.") == \
        ["Londra 14:30 → TSİ 16:30 · 17:30 yazılı değil"]


def test_tsi_birim_icinde_bir_kez_ve_saatli_adlar():
    # Birimde karşılığı verilmiş saat sonraki anışında yeniden istenmez.
    assert _neden("Fiksing Londra 16:00 (TSİ 18:00 ya da 19:00). Pencere Londra 16:00'da kapanır.") == []
    # Kuralın adındaki saat ad sayılır.
    assert _neden("NY IB 08:00 ve 09:30 kuralları; WM/R 16:00 fiksingi; New York ilk denge kırılımı — 08:00.") == []


def test_tsi_tablo_basligi_ve_izgara_notu():
    # Başlık satırında TSİ geçen tablonun saatleri TSİ'dir — işaret başlığın parantezinde dursa da.
    assert _neden("| Olay | Saat (TSİ) |\n|---|---|\n| karar | 21:00 |", tablo=True) == []
    assert _neden("| Olay | Saat |\n|---|---|\n| karar | 21:00 |", tablo=True) == ["şehri belirsiz"]
    # Parametre tablosunun değeri aynı bölümün ızgara notundaki karşılıkla kapanır (notsuz ikinci tablo); not
    # yanlışsa kapanmaz, başka bölümün notu da kapatmaz.
    mdx = ("## Bölüm\n\n| Parametre | Değer |\n|---|---|\n| son giriş | 10:00 |\n\n"
           "_Izgara: son giriş (Londra) 10:00 → TSİ yazın 12:00, kışın 13:00._\n\n"
           "Seçilen değerler:\n\n| Parametre | Seçilen |\n|---|---|\n| son giriş | 10:00 |\n")
    assert dg.tsi_metinde({"x": (mdx, None)}) == []
    h = dg.tsi_metinde({"x": (mdx.replace("kışın 13:00", "kışın 14:00"), None)})
    assert sorted(int(x.split(":")[1]) for x in h) == [5, 7, 13]      # iki tablo hücresi ve notun kendisi
    h = dg.tsi_metinde({"x": (mdx.replace("Seçilen değerler:", "## Öbür bölüm"), None)})
    assert [int(x.split(":")[1]) for x in h] == [13] and "şehri belirsiz" in h[0]


def test_tsi_figur_ogesi_kapsami():
    # Figür başlığında parantez dışındaki "TSİ" yalnız kendi öğesini (bir sonraki " · " ya da ";" e kadar) kapar.
    b = "Şekil 01 — Fiksing Londra 16:00 · TSİ 18:00 ya da 19:00 · kapanış 17:00"
    assert _neden(b, figur=True) == ["Londra 17:00 → TSİ 19:00 · 20:00 yazılı değil"]
    assert _neden(b) == []                                             # cümle kapsamı 17:00'yi de TSİ sayardı
    # Başlıktaki <br> sarmadır, cümle sonu değil.
    d = {"layout": {"title": {"text": "Şekil 02 — New York 08:30 verisi<br>TSİ 15:30 ya da 16:30"}}}
    assert dg.tsi_figurde("x", d) == []
    d["layout"]["title"]["text"] = "Şekil 02 — New York 08:30 verisi<br>sonraki satır"
    assert len(dg.tsi_figurde("x", d)) == 1


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


def test_tsi_metinde_butun_birimler():
    h = dg.tsi_metinde({"x": (MDX, None)})
    satirlar = sorted(int(x.split(":")[1]) for x in h)
    # 4: TSİ'siz madde · 6: tablo · 7: başlık · 8: figür başlığı · 9: etiket satırının ardındaki satır kendi
    # birimidir · 10: sayılı maddenin iki ucu. Karşılığı yazılmış paragraf ve madde geçer.
    assert satirlar == [4, 6, 7, 8, 9, 10, 10]


def test_tsi_birimleri():
    mdx = ("---\ntitle: 'Başlık Londra 08:00'\nkod: x\n---\n## Bölüm\nparagraf a\nparagraf b\n\n- madde\n"
           "<GrafikEmbed baslik=\"Şekil\" />\n| t |\n| u |\n\n_not satırı_\n\nson")
    assert list(dg._tsi_birimleri(mdx)) == [
        (2, "metin", "Başlık Londra 08:00", ""), (5, "metin", "Bölüm", "Bölüm"),
        (6, "metin", "paragraf a\nparagraf b", "Bölüm"), (9, "metin", "- madde", "Bölüm"),
        (10, "metin", "Şekil", "Bölüm"), (11, "tablo", "| t |\n| u |\n\n_not satırı_", "Bölüm"),
        (14, "metin", "_not satırı_", "Bölüm"), (16, "metin", "son", "Bölüm")]


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
