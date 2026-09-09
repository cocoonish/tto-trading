# -*- coding: utf-8 -*-
"""DİBS hattı duman sınaması — ağa çıkmaz, saniyeler sürer.

guncelle.py bu dosyayı hattın adımlarından ÖNCE koşturur; düşerse hat koşmaz.
Sınamada duran her madde bir gün gerçekten yanlış yayımlanmış (ya da yayını
durdurmuş) bir sayıdır.

08.09.2026 — SAYFANIN ADIYLA ÇAĞIRDIĞI ANAHTAR KOŞULLU ÜRETİLİYORDU. Dokuz yıl
düğümü o gün kurulamadı, `kiyas_*_9y_degisim_bp` çıpa gününün değerini
istediği için NaN çıktı ve `koy()` anahtarı ATLADI. Sayfa anahtarı adıyla
çağırıyor; yayın kapısı (sayfa sınavı 1) eksik anahtarı ENGEL saydı ve yayın
iş akışı arka arkaya üç kez düştü — günün bülteni saatlerce yayına çıkmadı.
Kural: sayfanın çağırdığı anahtar HER koşuda yazılır; ölçülebiliyorsa son dolu
günden ve kendi tarihiyle, ölçülemiyorsa boş ("—") — atlanmaz.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(BURASI))

SONUC: list[tuple[str, str]] = []


def sina(ad, fn):
    try:
        fn()
        SONUC.append(("✓", ad))
    except Exception as e:                                     # noqa: BLE001
        SONUC.append(("✗", f"{ad} — {type(e).__name__}: {e}"))


def _cerceve():
    gun = pd.bdate_range("2026-08-03", "2026-09-08")
    M = pd.DataFrame({"n2y": np.linspace(40.0, 38.0, len(gun)),
                      "n1y": np.linspace(41.0, 39.5, len(gun)),
                      "n9y": np.linspace(31.0, 30.5, len(gun))}, index=gun)
    return M


def _kiyas_son_dolu_gun():
    import ozet_uret as oz
    M = _cerceve()
    s_gun = pd.Timestamp("2026-09-08")
    g = pd.Timestamp("2026-08-10")
    # (1) çıpa dolu → değişim çıpaya kadar, bitiş çıpa günü
    r = oz.kiyas_degisim(M, s_gun, g, "n9y")
    assert r is not None
    bp, t1 = r
    assert t1 == s_gun, t1
    assert abs(bp - (M.loc[s_gun, "n9y"] - M.loc[g, "n9y"]) * 100) < 1e-9
    # (2) ÇIPA GÜNÜ BOŞ (08.09.2026 arızası) → son dolu gün alınır, bitiş o gün
    M2 = M.copy(); M2.loc[s_gun, "n9y"] = np.nan
    r = oz.kiyas_degisim(M2, s_gun, g, "n9y")
    assert r is not None, "çıpa günü boşken değişim ölçülemedi — anahtar düşer, yayın durur"
    bp2, t2 = r
    onceki = M2["n9y"].dropna().index[-1]
    assert t2 == onceki and t2 < s_gun, (t2, onceki)
    assert abs(bp2 - (M2.loc[onceki, "n9y"] - M2.loc[g, "n9y"]) * 100) < 1e-9
    # (3) son dolu gün TOLERANSIN DIŞINDA → None (bayat sayı basılmaz)
    M3 = M.copy(); M3.loc[M3.index > "2026-08-25", "n9y"] = np.nan
    assert oz.kiyas_degisim(M3, s_gun, g, "n9y") is None, \
        "on dört gün eski düğüm bugünün kıyası gibi yazılıyor"
    # (4) kıyas günü boş → None (başlangıç kaydırılmaz)
    M4 = M.copy(); M4.loc[g, "n9y"] = np.nan
    assert oz.kiyas_degisim(M4, s_gun, g, "n9y") is None
    # (5) tolerans sınırı kapsayıcı: tam ANLIK_TOLERANS_GUN gün eski düğüm kabul
    M5 = M.copy()
    sinir = s_gun - pd.Timedelta(days=oz.ANLIK_TOLERANS_GUN)
    M5.loc[M5.index > sinir, "n9y"] = np.nan
    r5 = oz.kiyas_degisim(M5, s_gun, g, "n9y")
    assert r5 is not None and (s_gun - r5[1]).days <= oz.ANLIK_TOLERANS_GUN


def _anahtar_atlanmaz():
    """Kıyas döngüsü ölçülemeyen değeri ATLAMAZ, boş yazar; bitişi damgalar.
    Kaynak metin sınanıyor: davranış koşturmadan, statik."""
    src = (BURASI / "ozet_uret.py").read_text(encoding="utf-8")
    i = src.index("# --- kıyas günleri")
    j = src.index("# --- ters eğri", i)
    blok = src[i:j]
    assert "kiyas_degisim(" in blok, "kıyas döngüsü ortak fonksiyonu kullanmıyor"
    assert 'O[f"{etiket}_{sonek}_degisim_bp"] = OLCULEMEDI' in blok, \
        "ölçülemeyen değişim boş yazılmıyor — anahtar düşer, yayın kapısı ENGEL üretir"
    assert 'O[f"{etiket}_{sonek}"] = OLCULEMEDI' in blok, "ölçülemeyen seviye boş yazılmıyor"
    assert '_degisim_bp_tarih"] = tr_tarih(t1)' in blok, \
        "değişimin bitiş günü damgalanmıyor — kaydırılmış uç çıpa günü gibi görünür"
    assert "float(M.loc[s_gun, kol])" not in blok, \
        "çıpa günü doğrudan okunuyor — boş düğümde NaN, anahtar düşer (08.09.2026)"
    import ozet_uret as oz
    assert oz.OLCULEMEDI == "—"


def _sayfa_anahtarlari():
    """Sayfaların bu hattan adıyla çağırdığı her anahtar, kıyas ailesindeyse
    döngünün ürettiği kalıba uymalı — sayfa yeni bir kıyas anahtarı çağırırsa
    burası onu adıyla söyler."""
    icerik = KOK / "site/src/content"
    if not icerik.exists():
        return
    kul: set[str] = set()
    for p in icerik.rglob("*.mdx"):
        kul |= set(re.findall(r'<Deger\s+proje="dibs-verim-egrisi"\s+anahtar="([^"]+)"',
                              p.read_text(encoding="utf-8")))
    kiyas = sorted(k for k in kul if k.startswith("kiyas_"))
    assert kiyas, "sayfa hiçbir kıyas anahtarı çağırmıyor — sınamanın hedefi değişmiş"
    kalip = re.compile(r"^kiyas_(1ay|3ay|1yil)(_(2y|1y|9y)(_degisim_bp)?)?$")
    uymayan = [k for k in kiyas if not kalip.match(k)]
    assert not uymayan, f"sayfa, döngünün üretmediği kıyas anahtarı çağırıyor: {uymayan}"


def _yukseklik_ay_adindan_bagimsiz() -> None:
    """Alt yazıdaki AY ADI figürün yüksekliğini oynatmamalı.

    Yükseklik alt yazının SATIR SAYISINDAN türüyor (`ust = 92 + 26 * len(alt)`)
    ve sayfa MDX'te aynı sayıyı ilan ediyor; sayfa sınavının 3. ölçütü sapmayı
    ENGEL sayar. Alt yazıya veriden gelen bir ay adı girdiğinde ("Çizilen anket
    Ağustos 2026, gerçekleşen TÜFE …") satır sayısı ay adının UZUNLUĞUNA bağlı
    hâle gelir: eylülde sarma değişirse yükseklik 26 px oynar, MDX eski sayıyı
    ilan eder ve YAYIN DURUR. Ölçüldü (09.09.2026): 12×12 = 144 ay bileşiminin
    hepsinde satır sayısı 3 — yani bugünkü metin güvenli. Bu sınama o ölçümü
    kilitliyor: alt yazı uzatılırsa ya da SATIR_SINIR değişirse burada düşer,
    yayın kapısında değil.
    """
    import re as _re
    kaynak = (BURASI / "grafik.py").read_text(encoding="utf-8")
    ad = {"re": _re}
    exec(_re.search(r"^SATIR_SINIR\s*=.*$", kaynak, _re.M).group(0), ad)
    exec(_re.search(r"^def _bol\(.*?(?=^def |\Z)", kaynak, _re.S | _re.M).group(0), ad)
    sablon = ("FREKANS UYUMSUZLUĞU: eğri GÜNLÜK, beklenti AYLIKTIR. Çizilen anket "
              "{a}, gerçekleşen TÜFE {t} ayına ait. PKA ayın 20'sinden (varsayım — anket "
              "resmî veri takviminde ayrı kalem değil), TÜFE ertesi ayın 3'ünden (TÜİK "
              "yayım günü; hafta sonuna denk gelirse ilk iş günü) itibaren geçerli "
              "sayılıp günlüğe yayılır.")
    aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    sayilar = {len(ad["_bol"](sablon.format(a=f"{a} 2026", t=f"{t} 2026")))
               for a in aylar for t in aylar}
    assert len(sayilar) == 1, (
        f"alt yazının satır sayısı ay adına göre değişiyor {sorted(sayilar)} — "
        "figür yüksekliği veriye bağlı hâle geldi, MDX'teki yukseklik={} bir ay "
        "sonra yanlışlanır ve yayın kapısı ENGEL verir")


sina("kıyas değişimi: çıpa boşsa son dolu gün, kendi tarihiyle", _kiyas_son_dolu_gun)
sina("kıyas anahtarı atlanmaz, boş yazılır; bitiş damgalanır", _anahtar_atlanmaz)


def _anlik_atlanmaz():
    """anlik(): metrik özetinde olmayan ya da çıpadan uzak anahtar boş yazılır,
    atlanmaz (08.09 kuralının anlık anahtarlara genellenmesi, 09.09.2026)."""
    kaynak = (BURASI / "ozet_uret.py").read_text(encoding="utf-8")
    bas = kaynak.index("    def anlik(")
    blok = kaynak[bas: kaynak.index("    for kaynak, hedef in (", bas)]
    assert blok.count("O[hedef_ad] = OLCULEMEDI") == 2, \
        "anlik(): iki düşme dalının ikisi de anahtarı boş yazmalı (atlamamalı)"
    assert "atlandı" not in blok.lower().replace("atlanmaz", ""), \
        "anlik() hâlâ 'atlandı' diyor — anahtar atlanmaz, boş yazılır"
    # Çıpadan uzak dalda son dolu gün damgalanır; özet dışı dalda damga yok.
    uzak = blok[blok.index("if yas > tolerans:"):]
    assert 'O[hedef_ad + "_tarih"] = tr_tarih(t)' in uzak.split("koy(hedef_ad")[0], \
        "çıpadan uzak anahtarın son dolu günü damgalanmıyor"
sina("anlık anahtar atlanmaz, boş yazılır; son dolu gün damgalanır", _anlik_atlanmaz)
sina("sayfanın çağırdığı kıyas anahtarları üretilen kalıpta", _sayfa_anahtarlari)

# ---------------------------------------------------------------------------
# 09.09.2026 — DÖRT KUSUR, HEPSİ "SAAT" SINIFINDAN (bütün hatların güncellik
# denetiminde ölçüldü):
#  (1) On bir aylık saat anahtarı ("pka_12a_tarih", "tufe_yillik_tarih",
#      "pka_ort_2y_tarih" …) "Ağustos 2026" diye Türkçe ay adıyla yazılıyordu;
#      ortak/bicim ile lib/bicim bu yazımı çözmez, yani bileşenin bayatlık
#      denetimi ve sayfa sınavının saat ölçütleri bu anahtarları hiç görmüyordu.
#  (2) Şekil saat defteri yoktu: sekiz figürün hepsi hattın ana saatiyle
#      (08.09) damgalanıyordu — taşıma figürü fonlama bacağıyla 07.09'da
#      biter, üç figür aylık bacak taşır.
#  (3) TÜFE günlüğe "ertesi ayın 5'i" kuralıyla yayılıyordu; TÜİK ayın
#      3'ünde yayımlar. Ağustos 2026 TÜFE'si 03.09 Perşembe çıktı, günlük seri
#      03.09 ve 04.09'da hâlâ Temmuz'un %31,75'ini taşıdı (Ağustos %31,51 ancak
#      07.09'da göründü): geriye dönük reel faiz iki gün yanlış paydayla
#      hesaplanıp sayfada "Ağustos 2026" etiketiyle basıldı.
#  (4) PKA yayım günü (20) bir varsayım ve sayfa onu ölçülmüş gibi yazıyordu.
# ---------------------------------------------------------------------------
def _ortak():
    """ortak/bicim ve okur_dili — PYTHONPATH'te yoksa depo kökünden."""
    import importlib
    try:
        return importlib.import_module("bicim"), importlib.import_module("okur_dili")
    except ImportError:
        sys.path.insert(0, str(KOK / "ortak"))
        return importlib.import_module("bicim"), importlib.import_module("okur_dili")


def _tufe_yayim_gunu():
    """(3) TÜFE ertesi ayın 3'ünden (hafta sonuysa ilk iş günü); PKA hafta
    sonuna düşen 20'si de kaydırılır; günlüğe yayma AYNI tanımı kullanır."""
    import metrik
    assert metrik.TUFE_YAYIM_GECIKME == 3, \
        "TÜFE yayım günü 3 değil — TÜİK ayın 3'ünde yayımlar; 5 iki iş günü sahte etiket üretir"
    assert metrik.PKA_YAYIM_GUN == 20
    # Ağustos 2026 → 03.09.2026 Perşembe (arızanın kendisi)
    assert metrik.yayim_gunu("2026-08-01", 3, ay_gecikme=1) == pd.Timestamp("2026-09-03")
    # Aralık 2025 → 03.01.2026 Cumartesi → 05.01.2026 Pazartesi
    assert metrik.yayim_gunu("2025-12-01", 3, ay_gecikme=1) == pd.Timestamp("2026-01-05")
    # PKA Eylül 2026: 20.09 Pazar → 21.09 Pazartesi
    assert metrik.yayim_gunu("2026-09-01", 20) == pd.Timestamp("2026-09-21")
    # Günlüğe yayılmış seri 03.09'da AĞUSTOS değerini taşımalı (eskiden 07.09)
    aylik = pd.Series([31.75, 31.51], index=pd.to_datetime(["2026-07-01", "2026-08-01"]))
    gun = pd.bdate_range("2026-08-20", "2026-09-08")
    g = metrik.gunluge_yay(aylik, gun, metrik.TUFE_YAYIM_GECIKME, ay_gecikme=1)
    assert g.loc["2026-09-02"] == 31.75 and g.loc["2026-09-03"] == 31.51, \
        f"03.09'da {g.loc['2026-09-03']} — Ağustos TÜFE'si yayım gününde seriye girmiyor"
    # Şekil 05'in dikey çizgileri de aynı tanımdan
    yg = metrik.yayim_gunleri(aylik, gun, metrik.TUFE_YAYIM_GECIKME, ay_gecikme=1)
    assert yg == [pd.Timestamp("2026-09-03")], yg
    src = (BURASI / "metrik.py").read_text(encoding="utf-8")
    govde = src[src.index("def gunluge_yay("):src.index("def yayim_gunleri(")]
    assert "yayim_gunu(" in govde, "gunluge_yay yayım gününü kendi hesaplıyor — tek tanım kırıldı"
    assert "replace(day=" not in govde


def _cerceve_ozet():
    a = {k + "_tarih": "2026-09-08" for k in
         ("n2y", "n1y", "reel_ileri", "fisher_basit_fark", "be_2y", "f_1y1y",
          "kelebek_1_2_5")}
    a.update({k + "_tarih": "2026-09-07" for k in
              ("n9y", "egim_2y9y", "carry_2y_tlref", "tlref")})
    return {"son_gun": "2026-09-08", "son_ay": "2026-08-01",
            "son_tufe_ay": "2026-08-01", "anlik": a}


def _sekil_saat_defteri():
    """(2) Her figür kendi ucunu taşır; karma figür iki parçalı, defter tek
    tarih ya da None; iki tüketici aynı fonksiyondan."""
    import metrik
    b, od = _ortak()
    o = _cerceve_ozet()
    d = metrik.sekil_saatleri(o, bugun="2026-09-09")
    assert set(d) == set(metrik.SEKIL_DOSYALARI)
    # grafik.py'nin yazdığı dosya adları defterle birebir
    gsrc = (BURASI / "grafik.py").read_text(encoding="utf-8")
    yazilan = set(re.findall(r'\("(\d\d_[a-z_]+\.html)",\s*\d\)', gsrc))
    assert yazilan == set(d), f"defter ↔ çizilen figürler ayrışmış: {yazilan ^ set(d)}"
    assert d["04_carry.html"] == "07.09.2026", d["04_carry.html"]      # fonlama bacağı bağlar
    assert d["03_egim_bukulme.html"] == "07.09.2026"                    # 2y−9y bağlar
    assert d["02_egri_hareketi.html"] == "08.09.2026"                   # seyrek 9y bağlamaz
    assert d["01_egri_bugun.html"] == d["08_tani_paneli.html"] == "08.09.2026"
    assert d["05_reel_faiz.html"] == "eğri 08.09.2026 · anket/TÜFE 08.2026", d["05_reel_faiz.html"]
    assert d["06_tufex_basabas.html"] == d["07_forward.html"] == "eğri 08.09.2026 · anket 08.2026"
    # Aylık bacakların EN ESKİSİ bağlar: TÜFE Temmuz'da kalmışsa 07.2026
    o2 = dict(o, son_tufe_ay="2026-07-01")
    assert metrik.sekil_saatleri(o2, bugun="2026-09-09")["05_reel_faiz.html"].endswith("07.2026")
    # min() yapısal: fonlama eğriden İLERİ olsa da eğri bağlar
    o3 = dict(o, anlik=dict(o["anlik"], carry_2y_tlref_tarih="2026-09-09"))
    assert metrik.sekil_saatleri(o3, bugun="2026-09-09")["04_carry.html"] == "08.09.2026"
    # Defter: karma → None + damga_ anahtarı; tek tarih çözülür, ertesi iş
    # gününden ileri değil (sayfa sınavı 18)
    defter, birlesik = metrik.defter_ayir(d)
    assert set(defter) == set(d)
    assert defter["05_reel_faiz.html"] is None and defter["04_carry.html"] == "07.09.2026"
    assert set(birlesik) == {"damga_05_reel_faiz", "damga_06_tufex_basabas", "damga_07_forward"}
    import datetime as _dt
    sinir = b.sonraki_is_gunu(_dt.date(2026, 9, 9))
    for v in defter.values():
        assert v is None or (b.tarihe_cevir(v) is not None and b.tarihe_cevir(v) <= sinir), v
    # Birleşik damga KIRK karakterin altında: cümle tarayıcı kırk ve üstünü
    # okur cümlesi sayar ve `AA.YYYY`yi ondalık sanır (ölçüldü: biçim uyarısı)
    for v in birlesik.values():
        assert len(v) < od.CUMLE_ESIK, f"damga cümle sayılır: {v!r} ({len(v)})"
        assert not od.ozet_cumleleri({"x": v}), v
    # Uzun yazım aynı yapıda, figürün alt başlığı için
    u = metrik.sekil_saatleri(o, uzun=True, bugun="2026-09-09")
    assert u["04_carry.html"] == "7 Eylül 2026" and u["06_tufex_basabas.html"].endswith("Ağustos 2026")
    # KAPANMAMIŞ AY: anket ayı yarına düşerdi; damga yalnız eğri bacağını taşır
    acik = dict(o, son_ay="2026-09-01", son_tufe_ay="2026-08-01")
    da = metrik.sekil_saatleri(acik, bugun="2026-09-22")
    assert da["06_tufex_basabas.html"] == "eğri 08.09.2026", da["06_tufex_basabas.html"]
    assert da["05_reel_faiz.html"] == "eğri 08.09.2026 · anket/TÜFE 08.2026"   # TÜFE ayı kapalı
    assert metrik.defter_ayir(da)[1].get("damga_06_tufex_basabas") == "eğri 08.09.2026", \
        "karma figür tek bacakla çıplak tarihe düşüp deftere kaçmamalı — MDX açık anahtar bekler"
    # Ölçüm yoksa None, uydurma yok
    bos = metrik.sekil_saatleri({"anlik": {}}, bugun="2026-09-09")
    assert all(v is None for v in bos.values()), bos
    # İki tüketici de AYNI fonksiyondan (kaynak metin)
    assert "metrik.sekil_saatleri(o, uzun=True)" in gsrc, "grafik.py figür damgasını defterden almıyor"
    assert "Çıpa: {damga}" in gsrc and gsrc.count("{damga}") == 8, gsrc.count("{damga}")
    osrc = (BURASI / "ozet_uret.py").read_text(encoding="utf-8")
    assert "metrik.defter_ayir(metrik.sekil_saatleri(m))" in osrc
    assert 'O["_sekil_tarih"] = defter' in osrc and "O.update(birlesik)" in osrc
    # MDX: karma figürler açık anahtarla çağrılır
    mdx = KOK / "site/src/content/projeler/dibs-verim-egrisi.mdx"
    if mdx.exists():
        m = mdx.read_text(encoding="utf-8")
        for kok in birlesik:
            assert f'tarihAnahtari="{kok}"' in m, f"MDX {kok} anahtarını çağırmıyor"
        # tek tarihli figürlere açık anahtar KONMAZ (18c çelişki riski)
        for dosya, v in defter.items():
            if v is not None:
                blok = m[m.index(dosya):m.index("/>", m.index(dosya))]
                assert "tarihAnahtari" not in blok, dosya


def _aylik_saat_anahtarlari():
    """(1) Aylık saat `AA.YYYY`, okur etiketi ayrı anahtarda (`_ay_ad`)."""
    import ozet_uret as oz
    b, od = _ortak()
    A = pd.DataFrame({"pka_12a": [23.95, 23.69], "pka_24a": [17.83, 18.03],
                      "pka_5y": [11.5, 11.14], "pka_faiz_12a": [29.44, 29.59],
                      "pka_faiz_24a": [21.76, 21.89], "pka_12a_n": [59.0, 63.0],
                      "tufe_2025": [132.31, 134.75]},
                     index=pd.to_datetime(["2026-07-01", "2026-08-01"]))
    d = oz.aylik_saatleri(A)
    on_bir = ("pka_12a", "pka_24a", "pka_5y", "pka_faiz_12a", "pka_faiz_24a",
              "pka_katilimci", "tufe_yillik", "pka_ort_1y", "pka_ort_2y",
              "pka_ort_5y", "pka_ort_7y")
    for k in on_bir:
        assert d[k + "_tarih"] == "08.2026", (k, d.get(k + "_tarih"))
        assert d[k + "_ay_ad"] == "Ağustos 2026"
        assert b.tarihe_cevir(d[k + "_tarih"]) is not None, "saat çözülmüyor"
    # Türkçe ay adı ve ISO saat anahtarına giremez
    for k, v in d.items():
        if k.endswith("_tarih"):
            assert re.fullmatch(r"\d{2}\.\d{4}", v), (k, v)
    assert oz.ay_kisa("2026-08-01") == "08.2026"
    # Kaynak: monthly `_tarih` artık ay_ad ile yazılmıyor
    src = (BURASI / "ozet_uret.py").read_text(encoding="utf-8")
    assert '_tarih"] = ay_ad(' not in src, "aylık saat anahtarı Türkçe ay adıyla yazılıyor"
    assert "O.update(aylik_saatleri(A))" in src
    # Sayfa etiketi AYRI anahtardan okuyor; saat anahtarı tabloda basılmıyor
    mdx = KOK / "site/src/content/projeler/dibs-verim-egrisi.mdx"
    if mdx.exists():
        m = mdx.read_text(encoding="utf-8")
        for k in ("pka_12a", "pka_24a", "pka_5y", "pka_ort_2y", "tufe_yillik"):
            assert f'anahtar="{k}_ay_ad"' in m, f"sayfa {k}_ay_ad çağırmıyor"
            assert f'anahtar="{k}_tarih"' not in m, f"sayfa {k}_tarih (AA.YYYY) basıyor"


def _anket_yayim_varsayimi():
    """(4) PKA yayım günü varsayımı okura yazılır; ek sayıya bağlı."""
    import metrik
    import ozet_uret as oz
    b, od = _ortak()
    for n, ek in ((1, "1'inden"), (3, "3'ünden"), (5, "5'inden"), (6, "6'sından"),
                  (9, "9'undan"), (10, "10'undan"), (20, "20'sinden"), (30, "30'undan")):
        assert metrik.gun_eki(n) == ek, (n, metrik.gun_eki(n))
    c = oz.anket_yayim_cumlesi(pd.Timestamp("2026-08-01"), 20)
    assert "varsayım" in c and "20.08.2026" in c and "Ağustos 2026" in c, c
    # Hafta sonuna düşen 20 kaydırılır: Eylül 2026 → 21.09.2026
    assert "21.09.2026" in oz.anket_yayim_cumlesi(pd.Timestamp("2026-09-01"), 20)
    # Okur dili: cümle kod dili taşımaz (ozet.json'un cümle alanı olarak taranır)
    bulgu = [x for x in od.kosu_kaydi_tara([c]) if x[1] in od.KOSU_KAYDI_ENGEL]
    assert not bulgu, bulgu
    src = (BURASI / "ozet_uret.py").read_text(encoding="utf-8")
    assert 'O["anket_yayim_cumlesi"]' in src and 'O["pka_yayim_metni"]' in src \
        and 'O["tufe_yayim_metni"]' in src
    assert "metrik.yayim_gunu(s_ay" in src, "anket gecikmesi yayım gününü kendi hesaplıyor"
    assert "replace(day=min(m[\"esik\"]" not in src
    mdx = KOK / "site/src/content/projeler/dibs-verim-egrisi.mdx"
    if mdx.exists():
        m = mdx.read_text(encoding="utf-8")
        for k in ("anket_yayim_cumlesi", "pka_yayim_metni", "tufe_yayim_metni"):
            assert f'anahtar="{k}"' in m, f"sayfa {k} çağırmıyor"
        assert "esik_tufe_yayim_gecikme\" ondalik={0}>5</Deger>'inden" not in m, \
            "sayfa sayının ardına sabit ek yapıştırıyor (3'inden çıkar)"


sina("TÜFE ertesi ayın 3'ünden, hafta sonu ilk iş günü; günlüğe yayma tek tanımdan",
     _tufe_yayim_gunu)
sina("şekil saat defteri: bağlayıcı bacak, iki parçalı damga, iki tüketici tek fonksiyon",
     _sekil_saat_defteri)
sina("aylık saat anahtarı AA.YYYY, okur etiketi ayrı anahtarda", _aylik_saat_anahtarlari)
sina("anket yayım günü varsayımı okura yazılır; ek sayıya bağlı", _anket_yayim_varsayimi)
sina("figür yüksekliği ay adından bağımsız (144 bileşimde satır sayısı sabit)",
     _yukseklik_ay_adindan_bagimsiz)



if __name__ == "__main__":
    for im, ad in SONUC:
        print(f"  {im} {ad}")
    dusen = [a for im, a in SONUC if im == "✗"]
    print(f"\n{len(SONUC) - len(dusen)}/{len(SONUC)} geçti")
    raise SystemExit(1 if dusen else 0)
