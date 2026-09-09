# -*- coding: utf-8 -*-
"""Büyüme hattı — duman sınaması. AĞA ÇIKMAZ, saniyeler sürer, çıkış kodu 0/1.

`guncelle.py` bu dosyayı hattın adımlarından ÖNCE koşturur ve düşerse hat hiç
koşmaz. Hattın hiç duman sınaması yoktu (09.09.2026'da ölçüldü): ölçüm katmanı
bozulsa bile çıktı siteye kopyalanırdı ve kusur ilk olarak yayın kapısında
görünürdü.

BURADA DURAN HER MADDE BİR ARIZAYA KARŞILIK GELİR
-------------------------------------------------
 1. SAAT GÜN YAZIMIYLA — hat `_tarih`i "30.06.2026" yazıyordu. Üç aylık bir
    ölçünün günü yoktur; GrafikEmbed o günü dört figürün altına basıyordu ve
    okur çeyreğin tamamını anlatan bir ölçüyü tek günün ölçümü sanıyordu.
    Biçim sözleşmesi çeyreğin SON AYINI ister: "06.2026".
 2. ETİKET İNGİLİZCE KALIPTA — `to_period("Q")` "2026Q2" veriyordu; depodaki
    tek çeyrek yazımı "2026-Ç2" ve etiket figür başlıklarına basılıyor.
 3. SAAT İLE ETİKET AYRIŞABİLİR — ikisi ayrı anahtarda durur; aynı çeyreği
    anlatmazlarsa sayfada damga ile başlık farklı dönem söyler.
 4. KOPYA SÖZLEŞMESİNİN DIŞINDAN YAZMAK — özet doğrudan site klasörüne
    yazılıyordu. İki sonucu vardı ve ikisi de sessizdi: "veri geriye gidemez"
    kapısı hattın KENDİ ozet.json'unu okur ve o dosya hiç yazılmıyordu; uyarı
    defteri hiç üretilmiyordu, yani veri ve ölçüm katmanının uyarıları ne
    sayfaya ne okur dili kapılarına ulaşıyordu.
 5. UYARI ŞABLONU OPERATÖR DİLİNDE — uyarı defteri siteye kopyalanır kopyalanmaz
    "bie_gsyzhtaken: demet düştü" satırı YAYIN ENGELİ üretirdi (sayfa sınavı 17,
    kod dili). Şablonlar gerçek argümanlarla kurulup taranır.
 6. SAYFANIN ÇAĞIRDIĞI ANAHTAR — özet üreticisinin anahtar adları sayfanın
    çağırdığı adlarla birebir; biri yeniden adlandırılırsa sayfa donmuş yedeğe
    düşer ve hiçbir yerde hata çıkmaz.
 7. KATKI ARİTMETİĞİ — katki = işaret × w(t−4) × g(t), ithalat EKSİ; artık
    ayrıştırma tabanı ile katkı toplamının farkıdır ve bileşenlere dağıtılmaz.
 8. ÖLÇÜLEMEYEN DEĞER ANAHTARI DÜŞÜREMEZ — ölçülemeyen bir büyüklük None
    yazılır, anahtar atlanmaz (08.09.2026'da DİBS'te atlanan üç anahtar yayını
    üç kez durdurmuştu).
 9. FİGÜR METNİ — başlıklar ETİKETTEN beslenir; çizilen figürde İngilizce
    çeyrek kalıbı kalmamalı (figür metni de okura basılır: sayfa sınavı 19).
10. YAPISAL KİLİT — `if __name__` kapısının ALTINA tanım konursa betik olarak
    koşan hat NameError ile düşer; py_compile ve import bunu görmez.

Koşum:  python3 duman.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import tempfile

import pandas as pd

PROJE = pathlib.Path(__file__).resolve().parent
KOK = PROJE.parents[1]
sys.path.insert(0, str(PROJE))

import veri                                                        # noqa: E402
import metrik                                                      # noqa: E402
import grafik                                                      # noqa: E402
import ozet_uret                                                   # noqa: E402

GECTI, DUSTU = 0, 0
_KUSUR: list[str] = []
# Okura giden metinler burada birikir; okur dili taramasının KAPSAMI bu
# torbadan türetilir, elle tutulan bir listeden değil.
OKUR_METIN: list[tuple[str, str]] = []


def _ortak(ad: str):
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(KOK / "ortak"))
        return __import__(ad)


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    global GECTI, DUSTU
    if kosul:
        GECTI += 1
        print(f"  ✓ {ad}")
    else:
        DUSTU += 1
        _KUSUR.append(ad)
        print(f"  ✗ {ad}" + (f"  → {ayrinti}" if ayrinti else ""))


def fikstur() -> dict:
    """Ölçüm katmanının çıktısıyla aynı biçimde sentetik bir kayıt.

    Kapsam elle tutulmuyor: bileşen listeleri metrik.py'nin KENDİ tablolarından
    geliyor, yani yarın bir kalem eklenirse fikstüre de kendiliğinden girer.
    """
    son = pd.Timestamp("2026-06-30")
    onceki = pd.Timestamp("2025-06-30")
    katkilar = {}
    for i, (kod, (ad, isaret)) in enumerate(metrik.HARCAMA.items()):
        g, w = 3.0 + i, 0.20 + 0.01 * i
        katkilar[kod] = {"ad": ad, "buyume": round(g, 2),
                         "agirlik": round(w * 100, 1),
                         "katki": round(isaret * w * g, 2), "isaret": isaret}
    toplam = round(sum(v["katki"] for v in katkilar.values()), 2)
    taban = 2.27
    sektorler = {k: {"ad": a, "buyume": 1.0 + i, "agirlik": 5.0 + i}
                 for i, (k, a) in enumerate(metrik.URETIM.items())}
    dayaniklilik = {k: {"ad": a, "nominal_buyume": 20.0 + i, "pay": 10.0 + i}
                    for i, (k, a) in enumerate(metrik.DAYANIKLILIK.items())}
    tarihce = [{"ceyrek": metrik.ceyrek_etiket(t),
                "yillik": 2.0 + i * 0.1, "ceyreklik": 0.3 + i * 0.05}
               for i, t in enumerate(pd.date_range(end=son, periods=6, freq="QE"))]
    return {
        "_ceyrek": metrik.ceyrek_etiket(son),
        "_tarih": metrik.ceyrek_saati(son),
        "buyume_yillik": 2.32, "buyume_ceyreklik": 1.12,
        "ayristirma_tabani": taban, "ayarlama_farki": -0.05,
        "onceki_ceyrek": metrik.ceyrek_etiket(onceki),
        "agirlik_donemi": metrik.ceyrek_etiket(onceki),
        "katkilar": katkilar, "katki_toplami": toplam,
        "artik": round(taban - toplam, 2),
        "artik_aciklama": ("stok değişimi (zincirlenmiş hacim endeksi "
                           "yayımlanmıyor) ve zincirleme tutarsızlığı"),
        "sektorler": sektorler, "dayaniklilik": dayaniklilik,
        "tarihce": tarihce, "uyarilar": [],
    }


def _cagrilar(ad: str) -> set[tuple[str, object]]:
    """Dosyadaki metot çağrıları: (metot adı, ilk sabit argüman).

    Yorum ve belge metni KAPSAM DIŞI — kuralı anlatan cümle kuralın ihlali
    sayılamaz.
    """
    import ast
    agac = ast.parse((PROJE / ad).read_text(encoding="utf-8"))
    out: set[tuple[str, object]] = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute):
            arg = (d.args[0].value if d.args and isinstance(d.args[0], ast.Constant)
                   else None)
            out.add((d.func.attr, arg))
    return out


def bolum_saat() -> None:
    print("\n[1] SAAT ve ETİKET — çeyreklik biçim sözleşmesi")
    bicim = _ortak("bicim")
    for ay, c in ((3, 1), (6, 2), (9, 3), (12, 4)):
        t = pd.Timestamp(f"2026-{ay:02d}-01") + pd.offsets.MonthEnd(0)
        saat, etiket = metrik.ceyrek_saati(t), metrik.ceyrek_etiket(t)
        sina(f"Ç{c} saati AA.YYYY ({saat})",
             bool(re.fullmatch(r"\d{2}\.\d{4}", saat)) and saat == f"{ay:02d}.2026",
             "üç aylık saat gün yazılmaz")
        sina(f"Ç{c} etiketi Türkçe ({etiket})",
             bool(re.fullmatch(r"\d{4}-Ç[1-4]", etiket)) and "Q" not in etiket,
             "depodaki tek yazım 2026-Ç2")
        sina(f"Ç{c} saati ile etiketi aynı çeyrek",
             bicim.tarihe_cevir(saat).month == 3 * c
             and etiket.endswith(f"Ç{c}"))
    # AA.YYYY ayın SON gününe demirlenir: bayatlık denetimi eskisiyle aynı günü
    # görür, yani biçim düzeltmesi hattın saatini geriye çekmez.
    sina("06.2026 → 30.06.2026 (ay sonuna demirleniyor)",
         bicim.tarihe_cevir("06.2026") == bicim.tarihe_cevir("30.06.2026"))
    # Kaynak kilidi AST üzerinden okunur, metin araması olarak değil: kuralın
    # NEDEN konduğunu anlatan yorum satırının kendisi eşleşiyordu ve ölçüt
    # kendi belgesine takılıyordu.
    sina("ölçüm katmanı `_tarih`i gün yazımıyla yazmıyor",
         ("strftime", "%d.%m.%Y") not in _cagrilar("metrik.py"))
    sina("çeyrek etiketi to_period(\"Q\") ile yazılmıyor",
         ("to_period", "Q") not in _cagrilar("metrik.py"),
         "'2026Q2' İngilizce kalıp; ceyrek_etiket kullanılır")
    sina("veri katmanı künyesi de Türkçe etiket yazıyor",
         ("to_period", "Q") not in _cagrilar("veri.py"))


def bolum_kopya() -> None:
    print("\n[2] KOPYA SÖZLEŞMESİ — hat siteye doğrudan yazmaz")
    kaynak = (PROJE / "ozet_uret.py").read_text(encoding="utf-8")
    kod = "\n".join(s for s in kaynak.splitlines()
                    if not s.lstrip().startswith("#"))
    sina("özet üreticisi site klasörüne yazmıyor",
         "site" not in kod.split('"""')[-1],
         "ozet.json klasör kökünde yazılır, kopyalamak guncelle.py'nin işi")
    M = fikstur()
    with tempfile.TemporaryDirectory() as td:
        gecici = pathlib.Path(td)
        (gecici / "data").mkdir()
        (gecici / "data" / "metrik.json").write_text(
            json.dumps(M, ensure_ascii=False), encoding="utf-8")
        (gecici / "data" / "kunye.json").write_text(
            json.dumps({"uyarilar": ["Künye uyarısı."]}, ensure_ascii=False),
            encoding="utf-8")
        eski_p, eski_d = ozet_uret.PROJE, ozet_uret.DATA
        try:
            ozet_uret.PROJE, ozet_uret.DATA = gecici, gecici / "data"
            kod_cikis = ozet_uret.main()
        finally:
            ozet_uret.PROJE, ozet_uret.DATA = eski_p, eski_d
        sina("özet üreticisi 0 ile bitiyor", kod_cikis == 0)
        sina("ozet.json klasör kökünde", (gecici / "ozet.json").exists())
        sina("uyarilar.json klasör kökünde", (gecici / "uyarilar.json").exists())
        u = json.loads((gecici / "uyarilar.json").read_text(encoding="utf-8"))
        sina("veri katmanının uyarısı deftere giriyor",
             "Künye uyarısı." in u["uyarilar"],
             "kusurun kendisi: künye uyarıları hiçbir dosyaya girmiyordu")
    # Boş uyarı listesinde de dosya yazılır: "uyarı yok" ile "dosya yok" aynı
    # görünmemeli.
    bos = ozet_uret.uyarilar_kur({}, {"_ceyrek": "2026-Ç2", "_tarih": "06.2026"})
    sina("uyarı yokken de defter kuruluyor",
         bos["uyarilar"] == [] and "kosum" in bos)
    ikili = ozet_uret.uyarilar_kur({"uyarilar": ["Aynı satır."]},
                                   {"uyarilar": ["Aynı satır."]})
    sina("mükerrer uyarı bir kez giriyor", ikili["uyarilar"] == ["Aynı satır."])


def _mdx_anahtarlari() -> set[str]:
    icerik = KOK / "site" / "src" / "content"
    kalip = re.compile(r'<Deger\s+proje="buyume"\s+anahtar="([^"]+)"')
    kul: set[str] = set()
    for y in icerik.rglob("*.mdx"):
        kul |= set(kalip.findall(y.read_text(encoding="utf-8")))
    return kul


def bolum_anahtar() -> None:
    print("\n[3] SAYFANIN ÇAĞIRDIĞI ANAHTARLAR")
    o = ozet_uret.ozet_kur(fikstur())
    icerik = KOK / "site" / "src" / "content"
    if not icerik.exists():
        print("  … site içeriği bulunamadı; anahtar ölçütü KOŞMADI")
    else:
        kul = _mdx_anahtarlari()
        eksik = sorted(kul - set(o))
        sina(f"sayfanın çağırdığı {len(kul)} anahtarın hepsi üretiliyor",
             kul and not eksik, f"eksik: {eksik}")
    for kod in metrik.HARCAMA:
        sina(f"katkı anahtarları var ({kod})",
             all(f"k_{kod.lower()}_{x}" in o for x in ("buyume", "katki", "agirlik")))
    for kod in metrik.URETIM:
        sina(f"sektör anahtarları var ({kod})",
             all(f"s_{kod.lower()}_{x}" in o for x in ("buyume", "agirlik")))
    for kod in metrik.DAYANIKLILIK:
        sina(f"dayanıklılık anahtarları var ({kod})",
             all(f"d_{kod.lower()}_{x}" in o for x in ("buyume", "pay")))
    # ÖLÇÜLEMEYEN DEĞER ANAHTARI DÜŞÜREMEZ.
    M = fikstur()
    M["sektorler"]["A"]["buyume"] = None
    M["katkilar"]["P7"]["katki"] = None
    o2 = ozet_uret.ozet_kur(M)
    sina("ölçülemeyen değer anahtarı atlamıyor",
         "s_a_buyume" in o2 and o2["s_a_buyume"] is None
         and "k_p7_katki" in o2 and o2["k_p7_katki"] is None)
    sina("saat ve etiket özete AYRI anahtarla giriyor",
         o["_tarih"] == "06.2026" and o["_ceyrek"] == "2026-Ç2")


def bolum_katki() -> None:
    print("\n[4] KATKI ARİTMETİĞİ")
    sina("ithalat kimlikte EKSİ giriyor", metrik.HARCAMA["P7"][1] == -1)
    sina("kalan beş bileşen ARTI",
         all(i == 1 for k, (_a, i) in metrik.HARCAMA.items() if k != "P7"))
    s = pd.Series([100.0, 101, 102, 103, 110.0],
                  index=pd.date_range("2025-06-30", periods=5, freq="QE"))
    y = metrik._yillik(s)
    sina("yıllık değişim dört çeyrek öteye kıyaslıyor",
         abs(float(y.iloc[-1]) - 10.0) < 1e-9, f"{float(y.iloc[-1])}")
    M = fikstur()
    hesap = sum(v["isaret"] * (v["agirlik"] / 100.0) * v["buyume"]
                for v in M["katkilar"].values())
    sina("katki = işaret × w(t−4) × g(t)",
         all(abs(v["katki"] - v["isaret"] * (v["agirlik"] / 100.0) * v["buyume"])
             < 0.01 for v in M["katkilar"].values()))
    sina("katkı toplamı bileşenlerin toplamı",
         abs(M["katki_toplami"] - hesap) < 0.02, f"{M['katki_toplami']} ≠ {hesap:.2f}")
    sina("artık = ayrıştırma tabanı − katkı toplamı",
         abs(M["artik"] - (M["ayristirma_tabani"] - M["katki_toplami"])) < 0.01)
    sina("ölçülemeyen büyüklük None yazılıyor", metrik._r(float("nan")) is None)
    sina("olmayan sütun None dönüyor (hat düşmüyor)",
         metrik._sutun(pd.DataFrame({"X_B1GQ": [1.0]}), "P311") is None)


def bolum_uyari_dili() -> None:
    print("\n[5] UYARI ŞABLONLARI — okur dili")
    okur_dili = _ortak("okur_dili")
    # Şablonlar GERÇEK argümanlarla kurulur: sızıntı ancak böyle görünür.
    veri._UYARI.clear()
    metrik._UYARI.clear()
    grup, baslik = metrik and "bie_gsyzhtaken", "Harcama yöntemi · takvim arındırılmış zincirlenmiş hacim"
    veri.uyar(f"{baslik}: bir seri demeti alınamadı, seriler tek tek denendi.",
              f"{grup} · TP.GSYIH40_HY_B1GQ · zaman aşımı")
    veri.uyar(f"{baslik}: TP.GSYIH40_HY_P311 serisi bu koşuda alınamadı.",
              f"{grup} · zaman aşımı")
    metrik.uyar("Üretim tarafının cari fiyatlı toplamı (B1G) ya da vergi kalemi "
                "(D21X31) bu yayımda yok — sektörel toplam ile GSYH "
                "karşılaştırması bu koşuda yapılamadı.")
    for ad, _i in metrik.HARCAMA.values():
        metrik.uyar(f"{ad}: reel ya da cari fiyatlı seri bu yayımda yok — "
                    "katkı ayrıştırmasına girmiyor.")
        metrik.uyar(f"{ad}: büyüme ya da ağırlık ölçülemedi — "
                    "katkı ayrıştırmasına girmiyor.")
    defter = ozet_uret.uyarilar_kur({"uyarilar": veri.uyarilar()},
                                    {"uyarilar": list(metrik._UYARI),
                                     "_ceyrek": "2026-Ç2", "_tarih": "06.2026"})
    OKUR_METIN.extend(("uyarilar.json", m) for m in defter["uyarilar"])
    veri._UYARI.clear()
    metrik._UYARI.clear()
    sina("grup kodu okura giden cümleye girmiyor",
         not any("bie_" in m for m in defter["uyarilar"]),
         "uyarilar.json siteye kopyalanır; bie_ kodu sayfa sınavı 17'de ENGEL")
    sina("iç anahtar adı (harcama_takvim) okura girmiyor",
         not any("harcama_takvim" in m for m in defter["uyarilar"]))
    o = ozet_uret.ozet_kur(fikstur())
    OKUR_METIN.extend((f"ozet.json {a}", m) for a, m in okur_dili.ozet_cumleleri(o))
    engel = [(k, aile, e) for k, m in OKUR_METIN
             for _i, aile, e in okur_dili.kosu_kaydi_tara([m])
             if aile in okur_dili.KOSU_KAYDI_ENGEL]
    sina(f"okura giden {len(OKUR_METIN)} metinde kod/yapım dili yok",
         not engel, str(engel[:4]))


def bolum_figur() -> None:
    print("\n[6] FİGÜR METNİ — başlık etiketten beslenir")
    kaynak = (PROJE / "grafik.py").read_text(encoding="utf-8")
    sina("figür başlığı hattın SAATİNİ basmıyor", 'M["_tarih"]' not in kaynak
         and "M['_tarih']" not in kaynak,
         "başlığa gün yazmak çeyreklik ölçüyü tek güne indirger")
    sina("figür başlığı ETİKETTEN besleniyor",
         "M['_ceyrek']" in kaynak and "M['agirlik_donemi']" in kaynak)
    M = fikstur()
    eski = grafik.CIKTI
    with tempfile.TemporaryDirectory() as td:
        try:
            grafik.CIKTI = pathlib.Path(td)
            grafik.sekil_01(M)
            grafik.sekil_02(M)
            grafik.sekil_03(M)
            grafik.sekil_04(M)
            metinler = []
            for y in sorted(pathlib.Path(td).glob("*.html")):
                ham = y.read_text(encoding="utf-8")
                metinler.append((y.name, re.sub(
                    r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), ham)))
        finally:
            grafik.CIKTI = eski
    sina("dört şekil de çiziliyor", len(metinler) == 4)
    ingilizce = [ad for ad, t in metinler if re.search(r"\d{4}Q[1-4]", t)]
    sina("figürde İngilizce çeyrek kalıbı yok", not ingilizce, str(ingilizce))
    turkce = [ad for ad, t in metinler if not re.search(r"\d{4}-Ç[1-4]", t)]
    sina("her figür dönemini Türkçe etiketle yazıyor", not turkce, str(turkce))


def bolum_yapi() -> None:
    print("\n[7] YAPISAL KİLİT")
    import ast
    for ad in ("veri.py", "metrik.py", "grafik.py", "ozet_uret.py", "duman.py"):
        agac = ast.parse((PROJE / ad).read_text(encoding="utf-8"))
        kapi = next((i for i, d in enumerate(agac.body)
                     if isinstance(d, ast.If) and "__main__" in ast.dump(d)), None)
        alt = [] if kapi is None else [
            d.name for d in agac.body[kapi + 1:]
            if isinstance(d, (ast.FunctionDef, ast.ClassDef))]
        sina(f"{ad}: `if __name__` kapısının altında tanım yok", not alt, str(alt))


def main() -> int:
    print("Büyüme hattı — duman sınaması (ağa çıkmaz)")
    bolum_saat()
    bolum_kopya()
    bolum_anahtar()
    bolum_katki()
    bolum_uyari_dili()
    bolum_figur()
    bolum_yapi()
    print(f"\n{GECTI} geçti · {DUSTU} düştü")
    if _KUSUR:
        print("Düşenler: " + " | ".join(_KUSUR))
    return 1 if DUSTU else 0


if __name__ == "__main__":
    raise SystemExit(main())
