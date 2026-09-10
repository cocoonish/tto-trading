# -*- coding: utf-8 -*-
"""Bütçe & borç stoku hattı — duman sınaması. AĞA ÇIKMAZ, saniyeler sürer, çıkış 0/1.

`guncelle.py` bu dosyayı hattın adımlarından ÖNCE koşturur ve düşerse hat hiç
koşmaz; `--denetle` de aynı yardımcıyı çağırır. Sınamada duran her madde bir gün
gerçekten yanlış yayımlanmış bir sayıdır (09.09.2026'da ölçüldü).

BURADA DURAN HER MADDE BİR ARIZAYA KARŞILIK GELİR
-------------------------------------------------
 1. SAAT SÖZLEŞMESİ — özetin okura basılan metin alanları ISO yazımı taşımaz:
    altı çıpa anahtarı ve stok cümlesi "2026-06" diye on üç yerde basılıyordu.
    Aylık saat AA.YYYY, gün GG.AA.YYYY; ölçüm katmanı ISO'da kalır, dönüşüm
    özet üreticisinde tek yerde.
 2. GECİKME YAYIM GÜNÜNDEN — bütçe bacağının gecikmesi ay BAŞINDAN sayılıyordu
    ve aynı bacak sayfada üç yaşla dolaşıyordu (metin 69 · şerit 39 · yayımdan
    bu yana 19). Ölçü BEKLENEN YAYIM GÜNÜNDEN (izleyen ayın 20'si, hafta sonu
    → ilk iş günü; resmî takvime karşı ölçüldü: Denge 15.09.2026, Borç Stoku
    21.09.2026) ve TEK tanımdan (veri.gecikme_gun) — iki katman da oradan.
 3. FİNANSAL HESAPLAR AYRI AİLE — GSYH ile aynı çeyreklik dosyada durur ama
    ayrı kurum ayrı takvimle yayımlar; tek ailede `max()` bacağın 161 günlük
    gecikmesini GSYH'nin 70'inin arkasına gizliyordu ve hiçbir ölçüye girmiyordu.
    Bacağın kendi saati (`finhesap_tarih`), kendi toleransı ve kendi uyarısı.
 4. BACAKTAN TÜREYEN ANAHTAR KENDİ SAATİNİ TAŞIR — net stok, BF.9, doğrulama
    farkları `<anahtar>_tarih` ile bacağın çeyreğini söyler; yoksa sayfa
    2026-Ç1'in sayısını hattın aylık saatiyle etiketler.
 5. AYNI ÇEYREK ÖZDEŞLİĞİ — Şekil 13 tablosunda brüt − nakit = net üçü aynı
    çeyrekten gelir; brüt stok GSYH çeyreğinden alınınca 14,93 − 2,75 ≠ 11,54
    görünüyor ve "aynı sayı değildir" cümlesi aynı sayıyı iki kez basıyordu.
 6. ŞEKİL 13'ÜN DAMGASI — figür "veri 2026-Ç2" diyordu, çizdiği her seri
    2026-Ç1'de bitiyordu; damga bacağın kendi çeyreğinden, özetle aynı listeden.
 7. TOLERANS TEK TANIM — özetin `tolerans_*` anahtarları veri.TAZELIK'ten;
    sayfadaki `bayatGun` finansal hesaplar bacağının toleransıyla aynı sayı.
 8. OKUR DİLİ — cümle alanları kod/yapım dili, anahtar adı ve biçim taşımaz.
 9. YAPISAL KİLİT — `bugun` iki giriş noktasına dışarıdan verilebilir (sınama
    duvar saatini dondurur); ay başından sayan eski kalıp geri konursa düşer.

Koşum:  python3 duman.py
"""
from __future__ import annotations

import inspect
import io
import json
import pathlib
import re
import shutil
import sys
import tempfile

import pandas as pd

BURASI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))

import veri                                                        # noqa: E402
import grafik                                                      # noqa: E402
import ozet_uret                                                   # noqa: E402

GECTI, DUSTU = 0, 0
_KUSUR: list[str] = []
MDX = BURASI.parents[1] / "site" / "src" / "content" / "projeler" / "butce-borc.mdx"


def _ortak(ad: str):
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(BURASI.parents[1] / "ortak"))
        return __import__(ad)


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    global GECTI, DUSTU
    if kosul:
        GECTI += 1
        print(f"  ✓ {ad}")
    else:
        DUSTU += 1
        _KUSUR.append(ad)
        print(f"  ✗ {ad}" + (f"\n      {ayrinti}" if ayrinti else ""))


ISO = re.compile(r"\d{4}-\d{2}(?!-Ç)")          # "2026-06" · "2026-06-30"; "2026-Ç1" etiket


# ===========================================================================
#  KUTU — özet üreticisi geçici dizinde, dondurulmuş duvar saatiyle
# ===========================================================================
def _kutu(bugun: str, fh_kirp: int = 0) -> dict:
    """ozet_uret.main()'i hattın depodaki veri dosyalarının KOPYASI üzerinde koşturur.

    fh_kirp > 0: çeyreklik metrikte finansal hesaplar bacağının son `fh_kirp`
    dolu çeyreği silinir — bacağın GSYH'den geride kaldığı hâl, verinin bugünkü
    durumundan bağımsız olarak kurulur (yarın iki bacak aynı çeyrekte bitse de
    sınama aynı arızayı görmeye devam eder).
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="butce-duman-"))
    (d / "data").mkdir()
    for y in (BURASI / "data").glob("*"):
        if y.is_file():
            shutil.copy(y, d / "data" / y.name)
    shutil.copy(BURASI / "uyarilar.json", d / "uyarilar.json")
    if fh_kirp:
        C = pd.read_csv(d / "data" / "ceyreklik_metrik.csv", index_col=0, parse_dates=True)
        fh = [k for k in C.columns if k in veri.FH_KOLONLAR
              or k in ("fh_borc_trl", "fh_borc_gsyh", "net_stok_trl",
                       "net_stok_gsyh", "net_fin_deger_gsyh")]
        dolu = C[list(veri.FH_KOLONLAR)].dropna(how="all").index
        for t in dolu[-fh_kirp:]:
            C.loc[t, fh] = float("nan")
        C.to_csv(d / "data" / "ceyreklik_metrik.csv")
    eski = (ozet_uret.PROJE, ozet_uret.VERI)
    out: dict = {}
    try:
        ozet_uret.PROJE, ozet_uret.VERI = d, d / "data"
        ozet_uret.O.clear()
        ozet_uret.EKSIK_DENETIM.clear()
        eski_cikti, sys.stdout = sys.stdout, io.StringIO()
        eski_hata, sys.stderr = sys.stderr, io.StringIO()
        try:
            ozet_uret.main(bugun)
            out["o"] = json.loads((d / "ozet.json").read_text(encoding="utf-8"))
            out["dur"] = None
        except SystemExit as ex:
            out["o"] = {}
            out["dur"] = str(ex)
        finally:
            out["stderr"] = sys.stderr.getvalue()
            sys.stdout, sys.stderr = eski_cikti, eski_hata
        out["C"] = pd.read_csv(d / "data" / "ceyreklik_metrik.csv", index_col=0,
                               parse_dates=True)
        out["m"] = json.loads((d / "data" / "metrik_ozet.json").read_text(encoding="utf-8"))
    finally:
        ozet_uret.PROJE, ozet_uret.VERI = eski
        ozet_uret.O.clear()
        ozet_uret.EKSIK_DENETIM.clear()
        shutil.rmtree(d, ignore_errors=True)
    return out


def _mdx_cagrilar() -> list[tuple[str, str]]:
    """MDX'teki (anahtar, etiketin tamamı) çiftleri."""
    metin = MDX.read_text(encoding="utf-8")
    return [(m.group(1), m.group(0))
            for m in re.finditer(r'<Deger proje="butce-borc" anahtar="([a-z0-9_]+)"[^>]*>', metin)]


# ===========================================================================
def bolum_saat() -> None:
    print("\n▶ Saat sözleşmesi (ISO yazımı okura gitmez)")
    sina("_ay_yaz: ISO ay → AA.YYYY", ozet_uret._ay_yaz("2026-06") == "06.2026")
    sina("_gun_yaz: ISO gün → GG.AA.YYYY", ozet_uret._gun_yaz("2026-06-30") == "30.06.2026")
    sina("_ay_yaz: ölçülmemiş (None) uydurulmaz", ozet_uret._ay_yaz(None) is None)
    k = _kutu("2026-09-08")
    o = k["o"]
    sina("özet üretildi", bool(o) and k["dur"] is None, k.get("dur") or k.get("stderr", "")[-300:])
    if not o:
        return
    sizan = [(a, v) for a, v in o.items() if isinstance(v, str) and ISO.search(v)]
    sina("hiçbir metin alanı ISO yazımı taşımıyor", not sizan, str(sizan[:5]))
    for a in ("deflator_taban", "tufe_son_ay", "stok_son_ay", "stok_ilk_ay",
              "senaryo_cipa_ay", "_tarih", "_tarih3", "akim_tarih", "finhesap_tarih"):
        sina(f"{a} AA.YYYY yazımında", bool(re.fullmatch(r"\d{2}\.\d{4}", str(o.get(a)))), repr(o.get(a)))
    sina("senaryo_cipa_ceyrek GG.AA.YYYY yazımında",
         bool(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", str(o.get("senaryo_cipa_ceyrek")))))
    sina("stok cümlesi ayı adıyla söylüyor (\"06.2026 itibarıyla\" değil)",
         "itibarıyla" in o.get("stok_cumlesi", "") and not ISO.search(o["stok_cumlesi"])
         and not re.search(r"\d{2}\.\d{4} itibarıyla", o["stok_cumlesi"]))
    bicim = _ortak("bicim")
    for a in ("_tarih", "_tarih2", "_tarih3", "akim_tarih", "finhesap_tarih"):
        sina(f"{a} ortak/bicim ile çözülüyor", bicim.tarihe_cevir(o.get(a)) is not None, repr(o.get(a)))


def bolum_gecikme() -> None:
    print("\n▶ Gecikme beklenen yayım gününden (tek tanım)")
    # Resmî takvime karşı ölçülen iki gün (TÜİK Ulusal Veri Yayımlama Takvimi,
    # Ağustos 2026 verisi): Denge 15.09.2026 Salı, Borç Stoku 21.09.2026 Pazartesi.
    sina("borç stoku: 20'si Pazar → 21.09.2026 Pazartesi",
         veri.beklenen_yayim("2026-08-01") == pd.Timestamp("2026-09-21"))
    sina("denge tablosu: 15.09.2026",
         veri.beklenen_yayim("2026-08-01", veri.DENGE_YAYIM_GUN) == pd.Timestamp("2026-09-15"))
    sina("Temmuz stoku 20.08.2026'da beklenir → 08.09'da 19 gün (69 değil)",
         veri.gecikme_gun("butce", "2026-07-01", "2026-09-08") == 19)
    sina("beklenenden ERKEN gelen veri eksi yaş üretmez",
         veri.gecikme_gun("butce", "2026-08-01", "2026-09-18") == 0)
    sina("öbür aileler gözlemin kendi tarihinden",
         veri.gecikme_gun("finhesap", "2026-03-31", "2026-09-08") == 161
         and veri.gecikme_gun("menkul", "2026-08-28", "2026-09-08") == 11)
    kaynak = inspect.getsource(veri.tazelik_denetimi)
    sina("veri katmanının tazelik denetimi aynı tanımdan ölçüyor",
         "gecikme_gun(" in kaynak and "(bugun - son).days" not in kaynak)
    kaynak_o = inspect.getsource(ozet_uret.main)
    sina("özet üreticisi aynı tanımdan ölçüyor (ay başından sayan kalıp yok)",
         'gecikme_gun("butce", s_ay, bugun)' in kaynak_o
         and "(bugun - s_ay).days" not in kaynak_o)
    k = _kutu("2026-09-08")
    o = k["o"]
    if not o:
        sina("özet üretildi", False, k.get("dur") or "")
        return
    s_ay = pd.Timestamp(k["m"]["son_ay"])
    beklenen = veri.gecikme_gun("butce", s_ay, "2026-09-08")
    sina("gecikme_butce_gun beklenen yayım gününden",
         o.get("gecikme_butce_gun") == beklenen, f"{o.get('gecikme_butce_gun')} ≠ {beklenen}")
    sina("beklenen yayım günü sayfaya adıyla yazılıyor",
         re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", str(o.get("beklenen_yayim_stok"))) is not None
         and o.get("yayim_gun_stok") == veri.STOK_YAYIM_GUN)
    sina("gecikme cümlesi bütçe bacağı için yayım gününü söylüyor",
         "beklenen yayım gününden" in o.get("gecikme_cumlesi", "")
         and str(o.get("gecikme_butce_gun")) in o.get("gecikme_cumlesi", ""))
    # MDX cümlesi tek ölçüye bağlı: "yayımından bu yana" + gecikme_butce_gun.
    metin = MDX.read_text(encoding="utf-8")
    i = metin.find('anahtar="gecikme_butce_gun"')
    sina("sayfa cümlesi 'yayımından bu yana' + gecikme_butce_gun",
         i > 0 and "yayımından bu yana" in metin[max(0, i - 160):i])
    sina("sayfa bütçe toleransını yayım gününden diye etiketliyor",
         "beklenen yayım gününden" in metin[metin.find('anahtar="tolerans_butce_gun"'):][:200])


def bolum_finhesap() -> None:
    print("\n▶ Finansal hesaplar ayrı aile, kendi saati ve toleransı")
    aile = {etiket: aile for etiket, _k, _b, _bas, _p, aile, _h in veri.KUMELER}
    sina("KUMELER: finansal hesaplar GSYH'den ayrı ailede",
         aile.get("Finansal hesaplar") == "finhesap" and aile.get("GSYH") == "ceyrek")
    sina("TAZELIK: finhesap ailesinin kendi toleransı var",
         "finhesap" in veri.TAZELIK and veri.TAZELIK["finhesap"][1] >= 180)
    # Veri katmanı: GSYH taze, finansal hesaplar eşiği aşmış → uyarı BACAĞI adıyla.
    bugun = pd.Timestamp("2026-09-08")
    q = pd.date_range("2024-03-31", "2026-06-30", freq="QE")
    c = pd.DataFrame(index=q)
    c["gsyh_cari"] = 1.0
    c["fh_yukum_toplam"] = 1.0
    c.loc[c.index > bugun - pd.Timedelta(days=250), "fh_yukum_toplam"] = float("nan")
    uy = veri.tazelik_denetimi({"ceyreklik": c}, bugun)
    fh_uy = [u for u in uy if "Finansal hesaplar" in u]
    sina("veri katmanı: finansal hesaplar eşiği aşınca KENDİ adıyla uyarıyor",
         bool(fh_uy), str(uy)[:300])
    sina("veri katmanı: GSYH tazeyken GSYH uyarısı yok",
         not [u for u in uy if "GSYH" in u], str(uy)[:300])
    sina("uyarı çeyreklik saati AA.YYYY yazıyor (\"31.12.2025\" değil)",
         bool(fh_uy) and re.search(r"son gözlemi \d{2}\.\d{4} ", fh_uy[0]) is not None,
         fh_uy[0] if fh_uy else "")
    c2 = c.copy()
    c2["fh_yukum_toplam"] = 1.0
    c2.loc[c2.index > bugun - pd.Timedelta(days=150), "fh_yukum_toplam"] = float("nan")
    uy2 = veri.tazelik_denetimi({"ceyreklik": c2}, bugun)
    sina("veri katmanı: meşru ritim (150 gün) uyarı üretmez",
         not [u for u in uy2 if "Finansal hesaplar" in u], str(uy2)[:300])
    # Özet: bacak GSYH'den bir çeyrek geride (enjekte edilmiş) → kendi saati ve gecikmesi.
    k = _kutu("2026-09-08", fh_kirp=1)
    o = k["o"]
    if not o:
        sina("özet üretildi (fh kırpılmış)", False, k.get("dur") or "")
        return
    bicim = _ortak("bicim")
    t_fh, t_q = bicim.tarihe_cevir(o.get("finhesap_tarih")), bicim.tarihe_cevir(o.get("_tarih3"))
    sina("finhesap_tarih GSYH bacağının saatinden geride", t_fh is not None and t_q is not None and t_fh < t_q,
         f"{o.get('finhesap_tarih')} / {o.get('_tarih3')}")
    sina("gecikme_finhesap_gun > gecikme_ceyrek_gun (gizlenmiyor)",
         isinstance(o.get("gecikme_finhesap_gun"), int)
         and o["gecikme_finhesap_gun"] > o.get("gecikme_ceyrek_gun", 10**6))
    sina("finhesap_ceyrek etiketi ayrı anahtarda (2026-Ç1 biçimi)",
         re.fullmatch(r"\d{4}-Ç[1-4]", str(o.get("finhesap_ceyrek"))) is not None)
    sina("tolerans_finhesap_gun özette ve TAZELIK ile aynı",
         o.get("tolerans_finhesap_gun") == veri.TAZELIK["finhesap"][1])
    sina("gecikme cümlesi finansal hesapları GSYH'den ayrı söylüyor",
         "Finansal hesaplar (" in o.get("gecikme_cumlesi", "")
         and "GSYH ve finansal hesaplar" not in o.get("gecikme_cumlesi", ""))
    eksik = [a for a in ozet_uret.FH_ANAHTARLAR if a in o and o.get(f"{a}_tarih") != o["finhesap_tarih"]]
    sina("bacaktan türeyen her anahtar bacağın saatini taşıyor", not eksik, str(eksik))
    eksik_d = [a for a in ("f34_fark", "f3_fark", "f4_fark", "f34_bant_min", "f3_fark_mutlak")
               if a in o and not re.fullmatch(r"\d{2}\.\d{4}", str(o.get(f"{a}_tarih")))]
    sina("doğrulama anahtarları kendi çeyreklik saatini taşıyor", not eksik_d, str(eksik_d))
    # Aynı çeyrek özdeşliği: brüt − nakit = net.
    if all(o.get(a) is not None for a in ("stok_fh_trl", "nakit_trl", "net_stok_trl")):
        sina("Şekil 13 tablosu: brüt − nakit = net AYNI çeyrekte",
             abs(o["stok_fh_trl"] - o["nakit_trl"] - o["net_stok_trl"]) < 0.02,
             f"{o['stok_fh_trl']} − {o['nakit_trl']} ≠ {o['net_stok_trl']}")
    else:
        sina("Şekil 13 tablosu: brüt − nakit = net", False, "anahtarlar üretilmedi")
    # Bacak eşiği aşınca bayat hükmü adıyla düşer (duvar saati ileri alınır).
    k2 = _kutu(str((pd.Timestamp(k["m"]["son_ceyrek"]) + pd.Timedelta(days=120)).date()), fh_kirp=1)
    o2 = k2["o"]
    sina("bacak toleransı aşınca bayat hükmü finansal hesapları adıyla yazıyor",
         bool(o2) and o2.get("bayat") is True and "Finansal hesaplar" in o2.get("bayat_cumlesi", ""),
         (o2 or {}).get("bayat_cumlesi", "")[:200])
    # Ölçülemeyen bacak: anahtar atlanmaz, boş yazılır.
    k3 = _kutu("2026-09-08", fh_kirp=10**6)
    o3 = k3["o"]
    sina("bacak hiç ölçülemezse etiket ve gecikme '—' (atlanmaz)",
         bool(o3) and o3.get("finhesap_ceyrek") == "—" and o3.get("gecikme_finhesap_gun") == "—"
         and "finhesap_tarih" not in o3 and o3.get("bayat") is True)


def bolum_sekil13() -> None:
    print("\n▶ Şekil 13'ün damgası bacağın kendi çeyreği")
    C = pd.read_csv(BURASI / "data" / "ceyreklik_metrik.csv", index_col=0, parse_dates=True)
    o = json.loads((BURASI / "data" / "metrik_ozet.json").read_text(encoding="utf-8"))
    fig = grafik.sekil_13(C, o, "SINAMA-DAMGASI")
    sina("sekil_13 verilen damgayı başlığa yazıyor",
         fig is not None and "SINAMA-DAMGASI" in str(fig.layout.title.text))
    kaynak = inspect.getsource(grafik.kos)
    sina("kos(): damga finansal hesaplar sütunlarından ölçülüyor (GSYH çeyreği değil)",
         "veri.bacak_ucu(C, veri.FH_KOLONLAR)" in kaynak and "sekil_13(C, o, damga_fh)" in kaynak)
    uc = veri.bacak_ucu(C, veri.FH_KOLONLAR)
    sina("bacak ucu en ESKİ sütun ucu (kıyas en eski bacağa kadar kurulur)",
         uc is not None and all(C[k].dropna().index[-1] >= uc for k in veri.FH_KOLONLAR if k in C.columns))
    sina("özet ile çizim aynı sütun listesinden ölçüyor",
         "FH_KOLONLAR" in inspect.getsource(ozet_uret) and not hasattr(ozet_uret, "FH_KOLONLAR_YEREL"))


def bolum_yigin() -> None:
    """Yığılı panelde eksik bacak SIFIR çizilemez.

    ARIZA (ölçülen 10.09.2026, YAYIMLANMIŞ figürde): Şekil 07'nin üç bacağı
    ayrı ritimde bitiyor (dış kredi 06.2026 · iç borç 07.2026 · eurobond
    08.2026). Her iz kendi indeksiyle çizildiği için plotly yığında eksik x'i
    SIFIR sayıyordu ve borç stoku okura 14,93 → 13,89 → 4,73 trilyon TL diye
    çıktı — iki ayda 10 trilyon TL'lik sahte bir çöküş. Sayfanın damgası
    DOĞRUYDU ("aylık 06.2026"); yalan söyleyen çizimdi.

    ÖLÇÜT KURALIN İLAN ETTİĞİ HÂLLERE KOŞTURULUR: hem bugünkü ağaç, hem de
    bacakların bilerek ayrıldığı sentetik hâl.
    """
    print("\n▶ Yığılı panel: eksik bacak sıfır çizilmiyor")
    import numpy as np

    def uclar(fig) -> dict:
        g: dict = {}
        for tr in fig.data:
            grup = getattr(tr, "stackgroup", None)
            if not grup:
                continue
            x, y = np.asarray(tr.x), np.asarray(tr.y, dtype="float64")
            dolu = np.flatnonzero(np.isfinite(y))
            if len(dolu):
                g.setdefault(grup, set()).add(pd.Timestamp(str(x[dolu[-1]])))
        return g

    M = pd.read_csv(BURASI / "data" / "aylik_metrik.csv", index_col=0, parse_dates=True)
    C = pd.read_csv(BURASI / "data" / "ceyreklik_metrik.csv", index_col=0, parse_dates=True)
    o = json.loads((BURASI / "data" / "metrik_ozet.json").read_text(encoding="utf-8"))
    S07 = ("ic_borc_trl", "dis_senet_trl", "dis_kredi_trl", "toplam_borc_trl")

    # (1) BUGÜNKÜ AĞAÇ — kural zaten ayrık bir hâl taşıyor.
    fig = grafik.sekil_07(M, C, o, grafik.ay_ad(pd.Timestamp(o["son_ay"])),
                          grafik.ceyrek_ad(pd.Timestamp(o["son_ceyrek"])))
    g = uclar(fig)
    sina("Şekil 07'nin yığın bacakları ORTAK uçta bitiyor",
         all(len(u) == 1 for u in g.values()), str({k: sorted(map(str, v)) for k, v in g.items()}))
    ilan = veri.bacak_ucu(M, S07)
    ciz = min(next(iter(g.values()))) if g else None
    sina("çizilen uç sayfanın İLAN ETTİĞİ uçla aynı (damga ile çizim ayrışmıyor)",
         ilan is not None and ciz == pd.Timestamp(ilan), f"ilan {ilan} · çizilen {ciz}")

    # (2) SENTETİK AYRIŞMA — bir bacak üç ay ileri gitse de yığın ortak uçta biter.
    M2 = M.copy()
    son = M2.index[-1]
    for ek in (1, 2, 3):
        yeni = son + pd.DateOffset(months=ek)
        M2.loc[yeni, "dis_senet_trl"] = 5.0
    M2 = M2.sort_index()
    fig2 = grafik.sekil_07(M2, C, o, "SINAMA", "SINAMA")
    g2 = uclar(fig2)
    sina("bir bacak üç ay ileri gitse de yığın ORTAK uçta bitiyor",
         all(len(u) == 1 for u in g2.values()),
         str({k: sorted(map(str, v)) for k, v in g2.items()}))
    sina("ileri giden bacak yığının ucunu İLERİ çekmiyor (en eski bağlayıcı)",
         bool(g2) and min(next(iter(g2.values()))) == pd.Timestamp(veri.bacak_ucu(M2, S07)))

    # (3) KAPI ÇAĞRI YERİNDE DEĞİL, ZORUNLU SON ADIMDA: yarın eklenecek bir
    #     yığın da kendiliğinden bu kuraldan geçsin.
    sina("hizalama _duzen'in içinde (her figürün zorunlu son adımı)",
         "_yigin_hizala(fig)" in inspect.getsource(grafik._duzen))
    sina("hizalama grubun KENDİ üyelerinden ölçüyor (elle kolon listesi yok)",
         "stackgroup" in inspect.getsource(grafik._yigin_hizala))


def bolum_sayfa() -> None:
    print("\n▶ Sayfa ↔ özet: tolerans tek tanım, bayatGun bacağın toleransı")
    cagrilar = _mdx_cagrilar()
    fh_set = set(ozet_uret.FH_ANAHTARLAR) | {
        f"{on}{ek}" for on in ("f34", "f3", "f4")
        for ek in ("_fark", "_bant_min", "_bant_max", "_fark_mutlak")}
    tol = veri.TAZELIK["finhesap"][1]
    yanlis = [(a, e) for a, e in cagrilar if a in fh_set
              and f"bayatGun={{{tol}}}" not in e]
    sina(f"finansal hesaplar anahtarlarının her çağrısında bayatGun={{{tol}}}",
         not yanlis, str(yanlis[:3]))
    fazla = [(a, e) for a, e in cagrilar if a not in fh_set and "bayatGun" in e]
    sina("bayatGun yalnız finansal hesaplar bacağında", not fazla, str(fazla[:3]))
    sina("sayfa finansal hesapları kendi çıpasıyla çağırıyor",
         any(a == "finhesap_ceyrek" for a, _e in cagrilar)
         and any(a == "gecikme_finhesap_gun" for a, _e in cagrilar)
         and any(a == "tolerans_finhesap_gun" for a, _e in cagrilar))
    metin = MDX.read_text(encoding="utf-8")
    iso_yedek = re.findall(r'anahtar="[a-z0-9_]+" ondalik=\{0\}[^>]*>\d{4}-\d{2}</Deger>', metin)
    sina("statik yedeklerde ISO ay yazımı yok", not iso_yedek, str(iso_yedek[:3]))


def bolum_okur_dili() -> None:
    print("\n▶ Okur dili (cümle alanları)")
    od = _ortak("okur_dili")
    k = _kutu("2026-09-08")
    o = k["o"]
    bulgu = []
    for ad, metin in od.ozet_cumleleri(o):
        for _i, aile, esl in od.kosu_kaydi_tara([metin]):
            bulgu.append((ad, aile, esl))
    sina("özetin cümle alanları temiz", not bulgu, str(bulgu[:5]))


def bolum_kilit() -> None:
    print("\n▶ Yapısal kilitler")
    sina("ozet_uret.main(bugun=…) dondurulabilir",
         "bugun" in inspect.signature(ozet_uret.main).parameters)
    sina("veri.tazelik_denetimi(…, bugun=…) dondurulabilir",
         "bugun" in inspect.signature(veri.tazelik_denetimi).parameters)
    sina("aile ölçüsü TAZELIK ile aile_gecikme aynı kümeyi taşıyor",
         set(veri.TAZELIK) - {"tufe"} == {"butce", "disborc", "menkul", "ceyrek", "finhesap", "kur"}
         and all(f'"{a}"' in inspect.getsource(ozet_uret.main) for a in veri.TAZELIK if a != "tufe"))


def main() -> int:
    print("Bütçe & borç stoku — duman sınaması (ağa çıkmaz)")
    for b in (bolum_saat, bolum_gecikme, bolum_finhesap, bolum_sekil13,
              bolum_yigin, bolum_sayfa, bolum_okur_dili, bolum_kilit):
        try:
            b()
        except Exception as ex:                                   # noqa: BLE001
            sina(f"{b.__name__} koştu", False, f"{type(ex).__name__}: {ex}")
    print(f"\n{GECTI} geçti · {DUSTU} düştü")
    if _KUSUR:
        print("DÜŞEN: " + " | ".join(_KUSUR))
    return 1 if DUSTU else 0


if __name__ == "__main__":
    raise SystemExit(main())
