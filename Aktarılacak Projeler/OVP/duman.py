# -*- coding: utf-8 -*-
"""OVP hattı — duman sınaması. AĞA ÇIKMAZ, saniyeler sürer, çıkış kodu 0/1.

`guncelle.py` bu dosyayı hattın adımlarından ÖNCE koşturur ve düşerse hat hiç
koşmaz. Sınama yalnız `--denetle` yazan birinin eline bırakılsaydı zamanlanmış
koşu onu hiç sormaz ve bozuk bir ölçüm katmanı çıktısını siteye kopyalamış
olurdu.

BURADA DURAN HER MADDE BİR ARIZAYA KARŞILIK GELİR
-------------------------------------------------
 1. İMA ARİTMETİĞİ — ima edilen kur, iki GSYH satırının oranıdır. Ters
    bölünürse sonuç sessizce 0,02 gibi bir sayı olur ve grafik yine çizilir.
 2. YÖNTEM SINAMASININ İKİ YÖNÜ — sınamaya yalnız KAPANMIŞ ve GERÇEKLEŞME
    sütunları girer. Tahmin (GT) sütunu girseydi ölçtüğümüz şey yöntem farkı
    değil tahmin hatası olurdu; açık yıl girseydi yarım yılın ortalaması yıl
    ortalaması sanılırdı.
 3. KALAN ORTALAMA ÖZDEŞLİĞİ — gerçekleşen ve kalan günlerin ağırlıklı
    ortalaması hedefi TAM verir. Paydayı yanlış almak (kalan yerine toplam)
    sessizce makul görünen ama yanlış bir sayı üretir.
 4. İKİ PATİKANIN AYNI ORTALAMAYI TUTTURMASI — iki varsayımın yakın çıkması
    sayfada bir SAĞLAMLIK sonucu olarak yayımlanıyor. O sonuç ancak iki patika
    da aynı kısıtı sağlıyorsa anlamlıdır; biri kısıtı sağlamazsa "yakınlık"
    bir tesadüftür.
 5. ZİNCİRİN HALKALARI — her yılın çıkışı sonrakinin girişi. Halka kopunca
    tablo yine dolu görünür ve devalüasyon satırları sessizce yanlış olur.
 6. TAŞIMANIN GÜN SAYIMI — lira bacağı GÖZLEM GÜNLERİ üzerinden bileşiklenir.
    Takvim günüyle hesaplamak aynı dönemde on puanı aşan bir fark üretiyor.
 7. İÇ TUTARLILIK — program tablosu elle tutuluyor; bir hücre kaydığında
    hiçbir yerde hata çıkmaz, yalnız sayfada yanlış bir sayı görünür.
 8. OKUR DİLİ — özetin cümle alanları ve figür metinleri sayfaya olduğu gibi
    basılır; dosya adı ve anahtar adı oraya girmemeli.
 9. ŞEKİL SAAT DEFTERİ — birleşik damga deftere yazılamaz (sayfa sınavı tek
    bir tarih ister ve çözemediğini ENGEL sayar); kapanmamış bir aya demirlenen
    damga yarına düşer.
10. YAPISAL KİLİT — ağa çıkan giriş noktasının içinde ağsız iş tutulamaz;
    tutulursa hiçbir kapı onu koşturmaz.

Koşum:  python3 duman.py
"""
from __future__ import annotations

import io
import json
import pathlib
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import veri                                                        # noqa: E402
import metrik                                                      # noqa: E402
import grafik                                                      # noqa: E402
import ozet_uret                                                   # noqa: E402

GECTI, DUSTU = 0, 0
_KUSUR: list[str] = []
# Üretilen okur metinleri burada birikir; okur dili taramasının KAPSAMI bu
# torbadan türetilir, elle tutulan bir listeden değil.
OKUR_METIN: list[tuple[str, str]] = []


def _ortak(ad: str):
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ortak"))
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


def _yakin(a, b, tol=1e-9) -> bool:
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


# ===========================================================================
#  SENTETİK ÇERÇEVE
# ===========================================================================
# Pencereler ÖLÇÜLENDİR: kur serisi 2015'ten bugüne günlük, iki program beş
# sütunlu. Sentetik olmasının sebebi denetlenebilirlik — gerçek seriyle
# sınamak, ölçütü verinin bugünkü hâline bağlar ve yarın veri değiştiğinde
# sınama sebepsiz düşer.
BU_YIL = 2026
SON_GUN = pd.Timestamp("2026-09-03")
KUR_BAS = pd.Timestamp("2023-01-02")


def _kur_serisi(bas=KUR_BAS, son=SON_GUN, s0=18.7, g=1.0009) -> pd.Series:
    """Sabit yüzdeli, iş günü ızgarasında bir kur serisi.

    Üstel seçildi çünkü hattın çözdüğü denklem de üstel: sentetik veriye
    kapalı çözümü bilinen bir patika koymak, ikiye bölmenin doğru yere
    yakınsadığını sınanabilir kılar.
    """
    idx = pd.bdate_range(bas, son)
    return pd.Series(s0 * g ** np.arange(len(idx)), index=idx, name="usdtry")


def _faiz_serisi(kur: pd.Series, oran: float = 36.5) -> pd.DataFrame:
    return pd.DataFrame({"tlref": oran, "politika": 37.0}, index=kur.index)


def _endeks_serisi(gecelik: pd.Series, yil: int) -> pd.Series:
    """Sentetik TLREF endeksi — gecelik faizden TAKVİM GÜNÜYLE kurulur.

    Kaynağın endeksi tam olarak bunu yapar: her kotasyon bir sonraki gözleme
    kadarki günleri taşır. Sentetik hâlini burada kurmak, hattın endeks yolunu
    ağa çıkmadan sınamayı ve iki yolun yakınlığını ÖLÇMEYİ mümkün kılıyor.
    """
    r = gecelik[gecelik.index.year == yil].dropna()
    gun = np.diff(r.index.to_numpy()).astype("timedelta64[D]").astype(float)
    gun = np.append(gun, 1.0)
    return pd.Series(100.0 * np.cumprod(1 + r.to_numpy() / 100 * gun / 365),
                     index=r.index)


def _tufe_serisi() -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", "2026-08-01", freq="MS")
    return pd.DataFrame({"tufe_12a": np.linspace(60.0, 31.5, len(idx))}, index=idx)


def _program(kod: str, yayin_ay: str, ilk_yil: int, tur: list[str],
             gsyh_tl: list[float], gsyh_usd: list[float],
             buyume: list[float], deflator: list[float],
             tufe: list[float]) -> dict:
    yillar = [str(ilk_yil + i) for i in range(len(tur))]
    return {
        "kod": kod, "ad": f"Sınama programı ({kod})", "kisa": kod,
        "yayin_ay": yayin_ay, "yayin_gun_olculdu": False,
        "yayin_notu": "sınama", "kaynak": "sınama",
        "sayfa": {"Tablo 1.1": 1},
        "sutun": dict(zip(yillar, tur)),
        "not": {},
        "deger": {
            "gsyh_tl": dict(zip(yillar, gsyh_tl)),
            "gsyh_usd": dict(zip(yillar, gsyh_usd)),
            "buyume": dict(zip(yillar, buyume)),
            "deflator": dict(zip(yillar, deflator)),
            "tufe": dict(zip(yillar, tufe)),
        },
    }


def _kayit(yeni: dict, eski: dict) -> dict:
    satir = json.loads(veri.PROGRAM_DOSYA.read_text(encoding="utf-8"))["satir"]
    return {"_kunye": {"ne": "sınama"}, "satir": satir,
            "programlar": [yeni, eski]}


def _ornek_kayit() -> dict:
    """İki sentetik program. Sayılar TUTARLI kurulur: nominal artış
    (1+büyüme)x(1+deflatör) özdeşliğini sağlar, yoksa iç tutarlılık ölçütü
    her senaryoda düşer ve asıl sınadığı şeyi göremez."""
    def tl(bas, buy, defl):
        out = [bas]
        for b, d in zip(buy[1:], defl[1:]):
            out.append(out[-1] * (1 + b / 100) * (1 + d / 100))
        return out

    buy_y = [3.7, 3.3, 4.2, 4.6, 5.0]
    def_y = [36.5, 30.6, 25.0, 14.5, 9.5]
    tl_y = tl(60000.0, buy_y, def_y)
    usd_y = [1500.0, 1700.0, 1900.0, 2000.0, 2100.0]
    yeni = _program("yeni", "2026-09", 2025,
                    ["gerceklesme", "tahmin", "program", "program", "program"],
                    tl_y, usd_y, buy_y, def_y, [30.9, 28.4, 21.0, 13.5, 9.0])
    buy_e = [3.3, 3.3, 3.8, 4.3, 5.0]
    def_e = [59.3, 35.0, 19.7, 10.9, 8.0]
    tl_e = tl(44000.0, buy_e, def_e)
    usd_e = [1350.0, 1550.0, 1650.0, 1750.0, 1850.0]
    eski = _program("eski", "2025-09", 2024,
                    ["gerceklesme", "tahmin", "program", "program", "program"],
                    tl_e, usd_e, buy_e, def_e, [44.4, 28.5, 16.0, 9.0, 8.0])
    return _kayit(yeni, eski)


# ===========================================================================
#  KUTU — ölçüm → çizim → özet UÇTAN UCA, geçici dizinde
# ===========================================================================
def _kutu(kur: pd.Series, faiz: pd.DataFrame | None = None,
          tufe: pd.DataFrame | None = None, kayit: dict | None = None,
          sekil: bool = True) -> dict:
    """Üç giriş noktasını GERÇEKTEN koşturur.

    Ağa çıkmayan iş ayrı fonksiyonlarda durduğu için buradan çağrılabiliyor;
    duman koşarken çalışan satır sayısı, hattın gerçek koşusunda çalışanın
    büyük kısmıdır. Bu depoda ölçülmüş bir kusur sınıfı tam buradaydı: ağa
    çıkan bir giriş noktasının İÇİNDEKİ ölçüm hiçbir kapı tarafından
    koşturulmuyordu.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="ovp-duman-"))
    (d / "data").mkdir()
    (d / "cikti").mkdir()
    prog_yol = d / "programlar.json"
    prog_yol.write_text(json.dumps(kayit or _ornek_kayit(), ensure_ascii=False),
                        encoding="utf-8")
    eski_yollar = (veri.PROJE, veri.VERI, veri.PROGRAM_DOSYA,
                   metrik.PROJE, metrik.VERI, grafik.CIKTI, grafik.VERI,
                   ozet_uret.PROJE, ozet_uret.VERI)
    cikti: dict = {}
    try:
        veri.PROJE, veri.VERI, veri.PROGRAM_DOSYA = d, d / "data", prog_yol
        metrik.PROJE, metrik.VERI = d, d / "data"
        grafik.CIKTI, grafik.VERI = d / "cikti", d / "data"
        ozet_uret.PROJE, ozet_uret.VERI = d, d / "data"
        veri._UYARI.clear()
        metrik._UYARI.clear()
        ozet_uret.O.clear()
        ozet_uret._ATLANAN.clear()
        pd.DataFrame({"usdtry": kur}).rename_axis("tarih").to_csv(d / "data" / "kur.csv")
        if faiz is not None and not faiz.empty:
            faiz.rename_axis("tarih").to_csv(d / "data" / "faiz.csv")
        if tufe is not None and not tufe.empty:
            tufe.rename_axis("tarih").to_csv(d / "data" / "tufe.csv")
        (d / "data" / "veri_durum.json").write_text(
            json.dumps({"cerceve_imza": veri.cerceve_imza(
                pd.DataFrame({"usdtry": kur})), "uyarilar": []}),
            encoding="utf-8")
        eski_cikti, sys.stdout = sys.stdout, io.StringIO()
        eski_hata, sys.stderr = sys.stderr, io.StringIO()
        try:
            metrik.kos()
            cikti["m"] = json.loads((d / "data" / "metrik_ozet.json").read_text(
                encoding="utf-8"))
            if sekil:
                try:
                    grafik.kos()
                    cikti["dur"] = None
                except SystemExit as ex:
                    cikti["dur"] = str(ex)
                cikti["html"] = {y.name: y.read_text(encoding="utf-8")
                                 for y in (d / "cikti").glob("*.html")}
            try:
                ozet_uret.main()
                cikti["o"] = json.loads((d / "ozet.json").read_text(encoding="utf-8"))
                cikti["ozet_dur"] = None
            except SystemExit as ex:
                cikti["o"] = {}
                cikti["ozet_dur"] = str(ex)
        except SystemExit as ex:
            cikti["metrik_dur"] = str(ex)
        finally:
            cikti["stderr"] = sys.stderr.getvalue()
            sys.stdout, sys.stderr = eski_cikti, eski_hata
        cikti["uyari"] = list(metrik._UYARI)
    finally:
        (veri.PROJE, veri.VERI, veri.PROGRAM_DOSYA, metrik.PROJE, metrik.VERI,
         grafik.CIKTI, grafik.VERI, ozet_uret.PROJE,
         ozet_uret.VERI) = eski_yollar
        shutil.rmtree(d, ignore_errors=True)
    return cikti


def _veri_kos(kur: pd.Series, kayit: dict | None = None) -> dict:
    """VERİ katmanının GİRİŞ NOKTASINI ağsız koşturur.

    Ağa çıkan tek çağrı (`cek_kume`) bir lambda ile değiştiriliyor ve
    `veri.kos()`un TAMAMI koşuyor: kapsam kapısı, ölçüm, dosya yazımı ve
    operatör dökümü dahil.
    """
    d = pathlib.Path(tempfile.mkdtemp(prefix="ovp-duman-veri-"))
    (d / "data").mkdir()
    prog_yol = d / "programlar.json"
    prog_yol.write_text(json.dumps(kayit or _ornek_kayit(), ensure_ascii=False),
                        encoding="utf-8")
    eski = (veri.PROJE, veri.VERI, veri.PROGRAM_DOSYA, veri.cek_kume,
            veri.FAIZ_DOSYA, veri.TUFE_DOSYA)
    out: dict = {}
    try:
        veri.PROJE, veri.VERI, veri.PROGRAM_DOSYA = d, d / "data", prog_yol
        veri.FAIZ_DOSYA = d / "yok_faiz.csv"
        veri.TUFE_DOSYA = d / "yok_tufe.csv"
        veri.cek_kume = lambda kodlar, yenile=False: pd.DataFrame(
            {"usdtry": kur}).rename_axis("tarih")
        veri._UYARI.clear()
        eski_cikti, sys.stdout = sys.stdout, io.StringIO()
        try:
            out["durum"] = veri.kos()
            out["dur"] = None
        except SystemExit as ex:
            out["durum"] = None
            out["dur"] = str(ex)
        finally:
            out["cikti"] = sys.stdout.getvalue()
            sys.stdout = eski_cikti
        out["dosya"] = sorted(y.name for y in (d / "data").glob("*"))
        out["uyari"] = list(veri._UYARI)
    finally:
        (veri.PROJE, veri.VERI, veri.PROGRAM_DOSYA, veri.cek_kume,
         veri.FAIZ_DOSYA, veri.TUFE_DOSYA) = eski
        shutil.rmtree(d, ignore_errors=True)
    return out


def _iz_kaynak(ad: str) -> str:
    """Bir fonksiyonun KAYNAK METNİ — davranışla sınanamayan sigortalar için.

    Bir sigorta kalktığında çıktı değişmez: ölü dal, hiç ateşlenmeyen doğru
    dalla tıpatıp aynı görünür. O yüzden kaynak metnin kendisi sınanır.
    """
    import inspect
    return inspect.getsource(getattr(veri, ad))


# ===========================================================================
def bolum_ima() -> None:
    print("\n▶ İma edilen kur aritmetiği")
    kayit = _ornek_kayit()
    p = veri.program(kayit, "yeni")
    ima = metrik.ima_kur(p)
    tl = veri.satir_serisi(p, "gsyh_tl")
    usd = veri.satir_serisi(p, "gsyh_usd")
    sina("ima = TL geliri ÷ dolar geliri",
         all(_yakin(ima[y], tl[y] / usd[y]) for y in ima),
         "Ters bölünseydi sonuç 0,02 mertebesinde çıkar ve grafik yine çizilirdi.")
    sina("ima, lira mertebesinde (ters bölünmemiş)",
         all(1 < v < 1000 for v in ima.values()))
    eksik = dict(p["deger"]["gsyh_usd"])
    eksik[list(eksik)[1]] = None
    p2 = json.loads(json.dumps(p))
    p2["deger"]["gsyh_usd"] = eksik
    sina("bir bacağı ölçülmemiş yıl imadan DÜŞER (sıfır ya da taşıma yok)",
         len(metrik.ima_kur(p2)) == len(ima) - 1,
         "Ölçülemeyen boş bırakılır; sıfır bir ölçüm sonucudur.")


def bolum_yontem() -> None:
    print("\n▶ Yöntem sınamasının iki yönü")
    kayit = _ornek_kayit()
    kur = _kur_serisi()
    ys = metrik.yontem_sinamasi(kayit, kur, BU_YIL)
    yillar = {(r["program"], r["yil"]) for r in ys}
    sina("KAPANMIŞ gerçekleşme sütunu sınamaya girer",
         ("eski", 2024) in yillar,
         f"girenler: {sorted(yillar)}")
    sina("TAHMİN (gerçekleşme tahmini) sütunu sınamaya GİRMEZ",
         ("eski", 2025) not in yillar and ("yeni", 2026) not in yillar,
         "O sütundaki fark yöntem farkı değil tahmin hatasıdır.")
    sina("PROGRAM sütunu sınamaya GİRMEZ",
         all(veri.sutun_turu(veri.program(kayit, r["program"]), r["yil"])
             == "gerceklesme" for r in ys))
    sina("AÇIK yıl sınamaya GİRMEZ",
         all(r["yil"] < BU_YIL for r in ys),
         "Yarım yılın ortalaması yıl ortalaması değildir.")
    # Farkın kendisi doğru mu: elde ölçülen ortalamaya karşı.
    for r in ys:
        oz = metrik.yil_ozeti(kur, r["yil"])
        sina(f"{r['yil']} farkı ima ÷ gerçekleşen − 1",
             _yakin(r["fark_yuzde"], (r["ima"] / oz["ortalama"] - 1) * 100, 1e-9))
    # Yılın tamamı elde yoksa sınama HİÇ kurulmaz.
    kisa = kur[kur.index >= "2024-07-01"]
    sina("yılın yarısı elde iken sınama kurulmaz",
         not [r for r in metrik.yontem_sinamasi(kayit, kisa, BU_YIL)
              if r["yil"] == 2024])
    # Eşiği aşan sapma UYARI üretir (ölçüm katmanının kendi kapısı).
    bozuk = json.loads(json.dumps(kayit))
    for p in bozuk["programlar"]:
        if p["kod"] == "eski":
            p["deger"]["gsyh_usd"]["2024"] *= 0.5
    k = _kutu(kur, kayit=bozuk)
    sina("eşiği aşan yöntem sapması uyarı üretir",
         any(u.startswith("YÖNTEM") for u in k.get("uyari", [])),
         f"uyarılar: {k.get('uyari')}")


def bolum_kalan() -> None:
    print("\n▶ Kalan günlerin gereken ortalaması")
    kayit = _ornek_kayit()
    kur = _kur_serisi()
    p = veri.program(kayit, "yeni")
    bu = metrik.bu_yil_olc(p, kur, BU_YIL)
    n, kalan = bu["n_gerceklesen"], bu["kalan_gun"]
    hedef, ger, gereken = (bu["ovp_ortalama"], bu["gerceklesen_ortalama"],
                           bu["gereken_ortalama"])
    sina("ağırlıklı ortalama özdeşliği hedefi TAM verir",
         _yakin((ger * n + gereken * kalan) / (n + kalan), hedef, 1e-9),
         f"n={n} kalan={kalan} hedef={hedef:.6f}")
    sina("kalan gün sayısı hafta içi günlerdir",
         kalan == int(np.busday_count(
             (pd.Timestamp(bu["son_gun"]) + pd.Timedelta(days=1)).date(),
             pd.Timestamp(f"{BU_YIL + 1}-01-01").date())))
    sina("gerçekleşen ortalama yalnız BU yılın gözlemlerinden",
         _yakin(ger, float(kur[kur.index.year == BU_YIL].mean()), 1e-9))
    sina("tatil payı ÖLÇÜLDÜ (varsayılmadı) ve kalan günü kısaltıyor",
         bu.get("kalan_tatil_ornek_yil", 0) > 0
         and (bu.get("kalan_gun_tatilsiz") is None
              or bu["kalan_gun_tatilsiz"] <= kalan))
    # PAYDA KUSURU: kalan yerine toplam güne bölmek makul görünen ama yanlış
    # bir sayı üretir; ölçüt farkın gerçekten büyük olduğunu gösterir.
    yanlis = (hedef * (n + kalan) - ger * n) / (n + kalan)
    sina("yanlış payda (toplam gün) belirgin biçimde başka bir sayı verir",
         abs(yanlis - gereken) > 0.5,
         f"doğru {gereken:.4f} ↔ yanlış {yanlis:.4f}")


def bolum_patika() -> None:
    print("\n▶ İki patika")
    s0, hedef, n = 48.0, 50.0, 85
    ust = metrik.ustel_cikis(s0, hedef, n)
    dog = metrik.dogrusal_cikis(s0, hedef, n)
    g = (ust / s0) ** (1 / n)
    ust_ort = float((s0 * g ** np.arange(1, n + 1)).mean())
    dog_ort = float(np.linspace(s0, dog, n + 1)[1:].mean())
    sina("üstel patika hedef ortalamayı tutturuyor", _yakin(ust_ort, hedef, 1e-6),
         f"ortalama {ust_ort:.8f} ≠ {hedef}")
    sina("doğrusal patika hedef ortalamayı tutturuyor", _yakin(dog_ort, hedef, 1e-9),
         f"ortalama {dog_ort:.8f} ≠ {hedef}")
    sina("iki patika AYNI kısıtı sağladığı için sonuçları yakın",
         abs(ust / dog - 1) < 0.01,
         "Yakınlık bir sonuçtur; iki patika farklı kısıt sağlasaydı tesadüf olurdu.")
    sina("erişilemeyen hedefte üstel çözüm None döner",
         metrik.ustel_cikis(48.0, 0.05, 85) is None,
         "Ölçülemeyen boş bırakılır; aralık dışı bir hedefe sayı uydurulmaz.")
    sina("sıfır gün ya da sıfır başlangıçta çözüm yok",
         metrik.ustel_cikis(0.0, 50.0, 85) is None
         and metrik.ustel_cikis(48.0, 50.0, 0) is None
         and metrik.dogrusal_cikis(48.0, 50.0, 0) is None)

    # ANA SAYFA MANŞETİ üstel patikayı yazıyor, yani okurun tabloda gördüğü
    # sayı iki varsayımdan BİRİNİ taşıyor. O seçimin savunması "fark bugün
    # küçük" değil, "fark yıl kapandıkça KÜÇÜLÜR"dür — ve bu bir veri gözlemi
    # değil, iki çözümün YAPISAL özelliği: n = 1'de patika tek adımdır, her iki
    # tanım da o adımı hedef ortalamaya eşitler. Ölçüldü (06.09.2026, gerçek
    # seriyle): 2026'da kalan 240 günde %0,429 → 97 günde %0,098; kapanmış
    # 2025'te 240 günde %0,686 → son günde %0,000.
    #
    # SINAMA BURADA DURUYOR ÇÜNKÜ: doğrusal çözüm bir kez "ortalama uçların
    # ortasıdır" kestirmesiyle yazılmıştı ve kısıtı SAĞLAMIYORDU. Kısıt
    # sınaması (yukarıda, 1e-9) onu yakalar. Ama YAKINLIK ölçütü yakalamıyor
    # ve bu ölçüldü: kestirme geri konsa n=85'te iki sayının farkı %0,0014'e
    # DÜŞÜYOR — doğru çözümün %0,0821'inden de küçük, çünkü kestirmenin hatası
    # ile üstel bükümü orada birbirini götürüyor. Yani "fark %1'in altında"
    # ölçütü, yazıldığı kusurun tam üstünde YEŞİL veriyor. Yakınlığın n'e göre
    # DAVRANIŞINI ise hiçbir ölçüt sormuyordu, oysa ana sayfada duran sayının
    # savunması tam olarak o davranış: kestirmede fark n=1'de %3,47'den
    # başlayıp düşüyor, yani MONOTONLUK TERSİNE dönüyor. Bir sayı
    # yayımlanıyorsa onu savunan cümle de sınanmalı.
    farklar = []
    for n in (1, 2, 5, 10, 20, 40, 85, 150, 240):
        u = metrik.ustel_cikis(48.21, 50.005, n)
        d = metrik.dogrusal_cikis(48.21, 50.005, n)
        farklar.append(abs(u / d - 1) * 100 if (u and d) else None)
    sina("tek adımlık patikada iki çözüm BİREBİR aynı (fark yapısal olarak sıfır)",
         farklar[0] is not None and farklar[0] < 1e-9,
         f"n=1'de fark %{farklar[0]}; iki tanım da tek adımı hedef ortalamaya eşitlemeli.")
    sina("iki patikanın farkı kalan gün azaldıkça KÜÇÜLÜYOR",
         all(a is not None and b is not None and a <= b + 1e-12
             for a, b in zip(farklar, farklar[1:])),
         "Fark n'de monoton artmıyorsa ana sayfa manşetinin savunması düşer: "
         f"{['%.6f' % f for f in farklar]}")
    sina("duyarlılık n'de DOYUYOR — asıl sürükleyen seviye ile hedefin arası",
         abs(farklar[-1] - farklar[6]) < 0.01
         and abs(metrik.ustel_cikis(42.86, 46.87, 85)
                 / metrik.dogrusal_cikis(42.86, 46.87, 85) - 1) * 100 > 0.3,
         "n=85 ile n=240 arası binde birken, uzak bir hedefte fark binde üçü aşar; "
         "manşet gerekçesi n'e değil MESAFEYE dayanır.")


def bolum_zincir() -> None:
    print("\n▶ Zincirin halkaları")
    kayit = _ornek_kayit()
    kur = _kur_serisi()
    p = veri.program(kayit, "yeni")
    bu = metrik.bu_yil_olc(p, kur, BU_YIL)
    yil_gun = metrik.gozlem_gunu_ortancasi(kur, BU_YIL)
    z = metrik.zincir_olc(p, bu, kur, BU_YIL, yil_gun)
    sina("zincir içinde bulunulan yıldan başlar", z and z[0]["yil"] == BU_YIL)
    sina("ilk halkanın girişi ÖNCEKİ yılın kapanışı",
         _yakin(z[0]["giris"], float(kur[kur.index.year == BU_YIL - 1].iloc[-1])))
    sina("ilk halkanın çıkışı üstel patikanın ucu",
         _yakin(z[0]["cikis"], bu["yil_sonu_ustel"]))
    sina("her halkanın girişi bir öncekinin ÇIKIŞI",
         all(_yakin(z[i]["giris"], z[i - 1]["cikis"]) for i in range(1, len(z))),
         "Halka koparsa tablo yine dolu görünür, devalüasyon satırları yanlış olur.")
    sina("devalüasyon çıkış ÷ giriş − 1",
         all(_yakin(r["deval_yuzde"], (r["cikis"] / r["giris"] - 1) * 100)
             for r in z))
    sina("reel lira ÇARPIMSAL (çıkarma değil)",
         all(_yakin(r["reel_tl_yuzde"],
                    ((1 + r["tufe_yuzde"] / 100) / (1 + r["deval_yuzde"] / 100) - 1)
                    * 100) for r in z if "tufe_yuzde" in r))
    fark = [abs(r["reel_tl_yuzde"] - r["makas_puan"]) for r in z
            if "makas_puan" in r]
    sina("çarpımsal ölçü ile çıkarma belirgin biçimde ayrışıyor",
         fark and max(fark) > 0.5,
         "Ayrışmasaydı iki ölçüyü ayrı yazmanın anlamı olmazdı.")
    # Sonraki yılların çıkışı da kendi ortalamasını tutturuyor.
    for r in z[1:]:
        g = (r["cikis"] / r["giris"]) ** (1 / r["gun"])
        ort = float((r["giris"] * g ** np.arange(1, r["gun"] + 1)).mean())
        sina(f"{r['yil']} çıkışı programın ortalamasını tutturuyor",
             _yakin(ort, r["ovp_ortalama"], 1e-6))
    km = metrik.kumule_olc(z)
    sina("kümüle kur, ilk giriş ile son çıkışın oranı",
         _yakin(km["kur_yuzde"], (z[-1]["cikis"] / z[0]["giris"] - 1) * 100))
    tf = 1.0
    for r in z:
        tf *= 1 + r["tufe_yuzde"] / 100
    sina("kümüle enflasyon yıl yıl BİLEŞİKLENİR (toplanmaz)",
         _yakin(km["tufe_yuzde"], (tf - 1) * 100, 1e-9))


def bolum_carry() -> None:
    print("\n▶ Taşımanın gün sayımı")
    kur = _kur_serisi()
    faiz = _faiz_serisi(kur, 36.5)
    # GECELİK BİR FAİZ TAKVİM GÜNÜ TAŞIR. Kotasyonları teker teker 1/365 ile
    # bileşiklemek hafta sonlarının faizini tamamen düşürür; gerçek seride
    # ölçülen fark 10,03 puan (resmî endeks +%29,61, gözlem günüyle +%19,58),
    # yani taşımanın kendisiyle aynı büyüklükte. Sınama bir zamanlar YANLIŞ
    # konvansiyonu kilitliyordu — bir kusuru sınamaya yazmak onu kalıcı yapar.
    c = metrik.carry_gerceklesen(kur, faiz["tlref"], BU_YIL)
    k = kur[kur.index.year == BU_YIL]
    takvim = (k.index[-1] - k.index[0]).days
    n = int((kur.index.year == BU_YIL).sum())
    gozlemle = ((1 + 36.5 / 100 / 365) ** n - 1) * 100
    takvimle = ((1 + 36.5 / 100 / 365) ** takvim - 1) * 100
    sina("endeks YOKKEN lira bacağı KOTASYONDAN, takvim günüyle kuruluyor",
         c["tl_yol"] == "kotasyon" and _yakin(c["tl_yuzde"], takvimle, 0.5),
         f"yol={c['tl_yol']} ölçülen {c['tl_yuzde']:.4f} ↔ takvim {takvimle:.4f}")
    sina("GÖZLEM günü konvansiyonu artık KULLANILMIYOR (eski kusur)",
         abs(c["tl_yuzde"] - gozlemle) > 5,
         f"ölçülen {c['tl_yuzde']:.2f} ↔ gözlemle {gozlemle:.2f}")
    # ENDEKS VARSA O KAZANIR: kaynağın kendi bileşik getirisi, bizim
    # türetmemizden önce gelir.
    _e = _endeks_serisi(faiz["tlref"], BU_YIL)
    ce = metrik.carry_gerceklesen(kur, faiz["tlref"], BU_YIL, _e)
    sina("endeks varsa lira bacağı ENDEKSTEN geliyor",
         ce["tl_yol"] == "endeks" and
         _yakin(ce["tl_yuzde"], (_e[_e.index.year == BU_YIL].iloc[-1]
                                 / _e[_e.index.year == BU_YIL].iloc[0] - 1) * 100,
                1e-9))
    sina("iki yol birbirine YAKIN (yedek yol endeksi yaklaşıyor)",
         abs(ce["tl_yuzde"] - c["tl_yuzde"]) < 2.0,
         f"endeks {ce['tl_yuzde']:.2f} ↔ kotasyon {c['tl_yuzde']:.2f}")
    # FİGÜR İLE ÖZET AYNI KONVANSİYONDAN. Ayrışırlarsa okur sayfadaki sayı ile
    # figürün son noktasını karşılaştırıp hangisinin doğru olduğunu bilemez.
    g = metrik.carry_gunluk(kur, faiz["tlref"], BU_YIL, _e)
    sina("günlük izin son noktası özetteki sayıyla AYNI",
         not g.empty and _yakin(float(g["net_yuzde"].iloc[-1]),
                                ce["net_yuzde"], 0.01),
         f"figür {float(g['net_yuzde'].iloc[-1]):.4f} ↔ özet {ce['net_yuzde']:.4f}")
    sina("kur bacağı yıl içi İLK gözleme göre",
         _yakin(c["kur_yuzde"], (k.iloc[-1] / k.iloc[0] - 1) * 100))
    sina("net getiri lira faktörü ÷ kur faktörü − 1",
         _yakin(c["net_yuzde"],
                ((1 + c["tl_yuzde"] / 100) / (1 + c["kur_yuzde"] / 100) - 1) * 100,
                1e-9))
    sina("yıllıklandırma TAKVİM günüyle",
         _yakin(c["yillik_yuzde"],
                ((1 + c["net_yuzde"] / 100) ** (365 / c["gun"]) - 1) * 100, 1e-9))
    # İleriye dönük: iki konvansiyon ve ikisi de ayrı ayrı doğru.
    kayit = _ornek_kayit()
    p = veri.program(kayit, "yeni")
    bu = metrik.bu_yil_olc(p, kur, BU_YIL)
    yil_gun = metrik.gozlem_gunu_ortancasi(kur, BU_YIL)
    z = metrik.zincir_olc(p, bu, kur, BU_YIL, yil_gun)
    ileri = metrik.carry_ileri(z, 37.0, yil_gun)
    sina("ileriye dönük basit konvansiyon (1+faiz) ÷ (1+deval) − 1",
         all(_yakin(r["basit_yuzde"],
                    (1.37 / (1 + r["deval_yuzde"] / 100) - 1) * 100) for r in ileri))
    bf = (1 + 37.0 / 100 / 365) ** yil_gun
    sina("ileriye dönük bileşik konvansiyon gözlem günü sayısıyla",
         all(_yakin(r["bilesik_yuzde"],
                    (bf / (1 + r["deval_yuzde"] / 100) - 1) * 100, 1e-9)
             for r in ileri))
    sina("iki konvansiyon ayrışıyor (ikisini yazmanın sebebi)",
         all(abs(r["basit_yuzde"] - r["bilesik_yuzde"]) > 1 for r in ileri))
    sina("faiz yoksa ileriye dönük taşıma HİÇ kurulmaz",
         metrik.carry_ileri(z, None, yil_gun) == [],
         "Faiz varsayımı olmadan yazılan bir taşıma uydurmadır.")


def bolum_tutarlilik() -> None:
    print("\n▶ İç tutarlılık")
    kayit = _ornek_kayit()
    t = veri.program_tutarlilik(kayit)
    sapan = [r for r in t if abs(r["sapma"]) > veri.TUTARLILIK_ESIK_PUAN]
    sina("tutarlı bir tabloda özdeşlikler sapma vermiyor", not sapan,
         f"sapanlar: {sapan[:2]}")
    sina("nominal gelir özdeşliği her yıl için ölçülüyor",
         len([r for r in t if r["ad"] == "nominal_gsyh"]) >= 8)
    bozuk = json.loads(json.dumps(kayit))
    bozuk["programlar"][0]["deger"]["deflator"]["2027"] += 5.0
    uy = veri.tutarlilik_uyarilari(veri.program_tutarlilik(bozuk))
    sina("bir hücre kayınca özdeşlik uyarı üretiyor", bool(uy),
         "Elle tutulan bir tabloda kayan hücre başka hiçbir yerde hata vermez.")
    OKUR_METIN.extend(("tutarlılık uyarısı", u) for u in uy)
    # Gerçek program kaydı da her koşuda sınanır — bu ölçüt DEPODAKİ dosyaya
    # bakar, sentetiğe değil.
    gercek = veri.program_tutarlilik(veri.programlar())
    kotu = [r for r in gercek
            if abs(r["sapma"]) > (veri.TUTARLILIK_ESIK_PUAN
                                  if r["birim"] == "puan" else 0.06)]
    sina("DEPODAKİ program kaydının özdeşlikleri tutuyor", not kotu,
         f"sapanlar: {[(r['program'], r['yil'], r['ad'], round(r['sapma'], 3)) for r in kotu][:4]}")
    sina("depodaki kayıt en az iki program taşıyor",
         len(veri.programlar()["programlar"]) >= 2)


def bolum_defter() -> None:
    print("\n▶ Şekil saat defteri")
    b = _ortak("bicim")
    kur = _kur_serisi()
    k = _kutu(kur, _faiz_serisi(kur), _tufe_serisi())
    m = k["m"]
    saat = veri.sekil_saatleri(m)
    sina("defter boş sözlükle çağrılabiliyor (künye onu basıyor)",
         isinstance(veri.sekil_saatleri({}), dict))
    sina("defterin anahtarları kaynak listeyle birebir",
         list(saat) == list(veri.SEKIL_DOSYALARI),
         f"{list(saat)} ≠ {list(veri.SEKIL_DOSYALARI)}")
    sina("panel künyesi kaynak listeyle birebir",
         sorted(grafik.PANEL_SAYISI) == sorted(veri.SEKIL_DOSYALARI))
    sina("zorunlu figür listesi kaynak listenin alt kümesi",
         set(veri.ZORUNLU_SEKIL) <= set(veri.SEKIL_DOSYALARI))
    defter, birlesik = veri.defter_ayir(saat)
    sina("defterdeki her değer ya None ya ÇÖZÜLEBİLİR tek tarih",
         all(v is None or b.tarihe_cevir(v) is not None for v in defter.values()),
         f"{defter}")
    sina("birleşik damga deftere GİRMİYOR",
         all(v is None or " · " not in v for v in defter.values()),
         "Sayfa sınavı defterde tek bir tarih ister ve çözemediğini engel sayar.")
    sina("her birleşik damga bir MDX anahtarına karşılık geliyor",
         all(a.startswith("damga_") for a in birlesik))
    yarin = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    sina("defterdeki hiçbir tarih yarından ileri değil",
         all(v is None or pd.Timestamp(b.tarihe_cevir(v)) <= yarin
             for v in defter.values()))
    # KAPANMAMIŞ AY: yayın günü ölçülmez, damga o parçayı yazmaz.
    p = veri.program(veri.programlar(), veri.program_kodlari(veri.programlar())[0])
    acik = json.loads(json.dumps(p))
    acik["yayin_ay"] = pd.Timestamp.today().strftime("%Y-%m")
    sina("kapanmamış ayda yayın günü ÖLÇÜLMEZ", veri.yayin_gunu(acik) is None,
         "Ayın son gününe demirlenen damga yarına düşerdi.")
    kapali = json.loads(json.dumps(p))
    kapali["yayin_ay"] = "2020-01"
    sina("kapanmış ayda yayın günü ölçülüyor",
         veri.yayin_gunu(kapali) is not None)
    ozet = k["o"]
    sina("özet defteri aynı fonksiyondan yazıyor",
         ozet.get("_sekil_tarih") == defter,
         "İki liste tutulsaydı figürün alt başlığı ile sayfadaki damga ayrışırdı.")


def bolum_kutu() -> None:
    print("\n▶ Ölçüm, çizim ve özet katmanları uçtan uca")
    kur = _kur_serisi()
    k = _kutu(kur, _faiz_serisi(kur), _tufe_serisi())
    sina("ölçüm katmanı düşmeden koştu", "metrik_dur" not in k,
         k.get("metrik_dur", ""))
    sina("çizim katmanı düşmeden koştu", k.get("dur") is None, k.get("dur") or "")
    sina("yedi figür de yazıldı", len(k.get("html", {})) == 7,
         f"{sorted(k.get('html', {}))}")
    sina("özet katmanı düşmeden koştu", k.get("ozet_dur") is None,
         k.get("ozet_dur") or "")
    o = k["o"]
    sina("hattın saati canlı bacakların EN YENİSİ",
         o.get("_tarih") == pd.Timestamp(k["m"]["kur_tarih"]).strftime("%d.%m.%Y"),
         f"{o.get('_tarih')} ↔ {k['m'].get('kur_tarih')}")
    sina("bayatlık hükmü EN GERİDE kalan bacaktan kuruluyor",
         o.get("veri_gecikme_blok") == veri.BLOK_OKUR["tufe"],
         f"{o.get('veri_gecikme_blok')}")
    sina("atlanan ölçüm yok", o.get("atlanan_olcum_sayisi") == 0,
         k.get("stderr", "")[:400])
    sina("isteğe bağlı anahtar listesi sayfaya yazılıyor",
         isinstance(o.get("_istege_bagli"), list) and o["_istege_bagli"])
    # LİRA FAİZİ DÜŞTÜĞÜNDE: taşıma anahtarları NULL olur, hat DURMAZ.
    k2 = _kutu(kur, None, _tufe_serisi())
    sina("faiz bacağı düşünce hat DURMUYOR", k2.get("ozet_dur") is None)
    o2 = k2["o"]
    sina("faiz bacağı düşünce taşıma anahtarları null yazılıyor",
         "carry_net" in o2 and o2["carry_net"] is None,
         "Anahtarın kaybolması sayfa sınavının 1. ölçütünde yayını durdururdu.")
    sina("faiz bacağı düşünce taşıma figürü üretilmiyor",
         "06_carry.html" not in k2.get("html", {}),
         f"{sorted(k2.get('html', {}))}")
    sina("zorunlu figürler faiz olmadan da üretiliyor",
         set(veri.ZORUNLU_SEKIL) <= set(k2.get("html", {})))


def bolum_durdurucu() -> None:
    print("\n▶ Durdurucu kapılar")
    # KAPSAM: ölçümün ihtiyacına yetmeyen bir tarihçe çıktı ÜRETMEZ.
    kisa = _kur_serisi(bas=pd.Timestamp("2026-01-02"))
    v = _veri_kos(kisa)
    sina("kapsam yetmeyince veri katmanı DURUYOR", v["dur"] is not None,
         "Kırpılmış bir tarihçeyle ima edilen kur ölçülemez.")
    sina("durunca dosya YAZILMIYOR", "kur.csv" not in v["dosya"],
         f"{v['dosya']}")
    # KAPSAM YETERLİ: giriş noktasının tamamı koşuyor.
    v2 = _veri_kos(_kur_serisi())
    sina("veri katmanının giriş noktası ağsız koşuyor", v2["dur"] is None,
         v2.get("dur") or "")
    sina("giriş noktası iki dosyayı da yazıyor",
         {"kur.csv", "veri_durum.json"} <= set(v2["dosya"]), f"{v2['dosya']}")
    sina("giriş noktası operatör dökümünü basıyor",
         "SON KUR GÜNÜ" in v2["cikti"])
    sina("durum kaydı çerçeve künyesini taşıyor",
         v2["durum"].get("cerceve_imza", "").count("·") == 2,
         f"{v2['durum'].get('cerceve_imza')}")
    # ZORUNLU FİGÜR: bir tanesi üretilemezse çizim katmanı DURUR.
    kur = _kur_serisi()
    eski = grafik.sekil_07
    try:
        grafik.sekil_07 = lambda o, damga: None
        k = _kutu(kur, _faiz_serisi(kur), _tufe_serisi())
    finally:
        grafik.sekil_07 = eski
    sina("zorunlu figür üretilemeyince çizim katmanı DURUYOR",
         k.get("dur") is not None and "zorunlu" in (k.get("dur") or ""),
         k.get("dur") or "")
    # PANEL KÜNYESİ: figüre panel eklenip künye güncellenmezse DURUR.
    eski_p = dict(grafik.PANEL_SAYISI)
    try:
        grafik.PANEL_SAYISI["01_ima_kur.html"] = 3
        k = _kutu(kur, _faiz_serisi(kur), _tufe_serisi())
    finally:
        grafik.PANEL_SAYISI.clear()
        grafik.PANEL_SAYISI.update(eski_p)
    sina("panel künyesi figürle ayrışınca çizim katmanı DURUYOR",
         k.get("dur") is not None and "panel" in (k.get("dur") or ""),
         k.get("dur") or "")
    # TARİHSİZ ÖZET: hiçbir saat kurulamıyorsa özet yayına GİREMEZ.
    m_eski = ozet_uret._saatler
    try:
        ozet_uret._saatler = lambda m: {}
        k = _kutu(kur, _faiz_serisi(kur), _tufe_serisi())
    finally:
        ozet_uret._saatler = m_eski
    sina("tarihsiz özet yayına GİREMEZ", k.get("ozet_dur") is not None,
         k.get("ozet_dur") or "")


def bolum_yapi() -> None:
    print("\n▶ Yapısal kilitler")
    kaynak = _iz_kaynak("kos")
    olcumler = ["kapsam_olc(", "bosluk_olc(", "tazelik_olc(",
                "cerceve_uyarilari(", "program_tutarlilik("]
    kalan = [c for c in olcumler if c in kaynak]
    sina("ağa çıkan giriş noktasında ölçüm çağrısı YOK", not kalan,
         f"kalanlar: {kalan} — duman ağa çıkmadığı için o satırlar hiçbir "
         "kapı tarafından koşturulmazdı.")
    sina("giriş noktası ölçen yarısını AYRI fonksiyondan çağırıyor",
         "durum_kaydi(" in kaynak and "kosu_dokumu(" in kaynak)
    sina("çekim penceresi önbellek adına yazılıyor",
         "alt_sinir" in _iz_kaynak("_cache_yolu"),
         "Pencere ada girmezse katalog geriye çekildiğinde kısa dosya taze görünür.")
    sina("bitiş ileri atılıyor (ertesi günün kuru bugün ilan ediliyor)",
         "ILERI_GUN" in _iz_kaynak("cek_kume"))
    sina("uzun aralık PARÇALI isteniyor",
         "PARCA_GUN" in _iz_kaynak("cek_kume"),
         "Tek istekte sorulan uzun aralığı kaynak sessizce kırpar.")
    sina("karma damgada program bacağı EN ESKİ programdan",
         "program_eski_yayin" in _iz_kaynak("sekil_saatleri"))
    # Kapıdan sonra tanım: guncelle.py'nin ön denetimiyle aynı soru, hattın
    # kendi içinde. Betik olarak koşan bir dosyada kapıdan sonraki bir `def`
    # NameError verir ve bütün adımları birden düşürür.
    import ast
    for ad in ("veri.py", "metrik.py", "grafik.py", "ozet_uret.py", "duman.py"):
        yol = pathlib.Path(__file__).resolve().parent / ad
        agac = ast.parse(yol.read_text(encoding="utf-8"))
        kapi = [d for d in agac.body if isinstance(d, ast.If)
                and ast.dump(d.test).count("__name__")]
        sinir = min((d.lineno for d in kapi), default=10 ** 9)
        sonra = [d.name for d in agac.body
                 if isinstance(d, (ast.FunctionDef, ast.ClassDef))
                 and d.lineno > sinir]
        sina(f"{ad}: kapıdan sonra tanım yok", not sonra, f"{sonra}")


def bolum_okur_dili() -> None:
    print("\n▶ Okur dili ve biçim")
    od = _ortak("okur_dili")
    kur = _kur_serisi()
    k = _kutu(kur, _faiz_serisi(kur), _tufe_serisi())
    o = k["o"]
    for alan, metin in od.ozet_cumleleri(o):
        OKUR_METIN.append((f"özet · {alan}", metin))
    for u in k.get("uyari", []):
        OKUR_METIN.append(("koşu kaydı", u))
    # Figür metinleri de okur metnidir: başlık ve alt yazı şeklin tam üstünde.
    import re as _re
    kalip = _re.compile(r'"(?:text|title)":"((?:[^"\\]|\\.){4,4000})"')
    for ad, ham in (k.get("html") or {}).items():
        for e in kalip.finditer(ham):
            OKUR_METIN.append((f"figür · {ad}", e.group(1)))
    sina("okur metni torbası dolu (kapsam üretilen metinden türetiliyor)",
         len(OKUR_METIN) > 20, f"{len(OKUR_METIN)} metin")
    engel = []
    for nerede, metin in OKUR_METIN:
        for aile, parca, _n in od.tara(metin):
            engel.append(f"{nerede} — {aile}: {parca}")
    sina("okura giden hiçbir metinde kod ya da yapım dili yok", not engel,
         " | ".join(engel[:6]))
    kayit_bulgu = []
    for _n, aile, parca in od.kosu_kaydi_tara(
            [m for nerede, m in OKUR_METIN if nerede.startswith("koşu kaydı")]):
        if aile in od.KOSU_KAYDI_ENGEL:
            kayit_bulgu.append(f"{aile}: {parca}")
    sina("koşu kaydında engel sınıfı bulgu yok", not kayit_bulgu,
         " | ".join(kayit_bulgu[:6]))
    b = _ortak("bicim")
    sina("sayı yazımı ondalık virgül ve eksi işareti taşıyor",
         b.sayi(-1234.5, 1) == "−1.234,5" and b.yuzde(-1.884, 2) == "−%1,88")
    nokta = [f"{nerede}: {metin}" for nerede, metin in OKUR_METIN
             if _re.search(r"(?<![\w.])\d+\.\d{1,2}(?![\w.])", metin)]
    sina("okur metninde ondalık NOKTA yok", not nokta, " | ".join(nokta[:4]))


def bolum_cumle() -> None:
    print("\n▶ Cümle sözleşmesi")
    kur = _kur_serisi()
    k = _kutu(kur, _faiz_serisi(kur), _tufe_serisi())
    o = k["o"]
    od = _ortak("okur_dili")
    uzun = []
    for alan, metin in od.ozet_cumleleri(o):
        if (alan in ozet_uret.CUMLE_OLCUSU_MUAF
                or alan.startswith(ozet_uret.CUMLE_OLCUSU_MUAF_ONEK)):
            continue
        import re as _re
        cumle = len(_re.findall(r"\.\s", metin)) + 1
        sayi = len(_re.findall(r"(?<![\w.])[−+]?\d+[.,]?\d*", metin))
        if cumle > ozet_uret.CUMLE_TAVAN or sayi > ozet_uret.SAYI_TAVAN * cumle:
            uzun.append(f"{alan}: {cumle} cümle / {sayi} sayı")
    sina("hiçbir cümle alanı tavanı aşmıyor", not uzun, " | ".join(uzun[:5]))
    sina("bayat cümlesi bulgu yokken de yazılıyor",
         isinstance(o.get("bayat_cumlesi"), str) and o["bayat_cumlesi"],
         "Bulgu varken yazılıp yokken düşen bir anahtar, hüküm tam "
         "yanlışlaştığı anda statik yedeğe düşerdi.")
    sina("uyarı cümlesi sayıyla çelişmiyor",
         (o.get("uyari_sayisi") == 0) == ("uyarı düşmedi" in o.get("uyari_cumlesi", "")))
    sina("yöntem cümlesi sınama kurulamadığında da yazılıyor",
         isinstance(o.get("yontem_cumlesi"), str) and o["yontem_cumlesi"])


def bolum_revizyon() -> None:
    print("\n▶ Revizyon")
    kayit = _ornek_kayit()
    rev = metrik.revizyon_olc(kayit, "yeni", "eski")
    sina("revizyon yalnız ORTAK yıllarda kuruluyor",
         {r["yil"] for r in rev} <= ({int(y) for y in kayit["programlar"][0]["sutun"]}
                                     & {int(y) for y in kayit["programlar"][1]["sutun"]}))
    yuzde = [r for r in rev if r["fark_birim"] == "%"]
    puan = [r for r in rev if r["fark_birim"] == "puan"]
    sina("seviye satırları YÜZDE olarak revize ediliyor",
         all(_yakin(r["fark"], (r["yeni"] / r["eski"] - 1) * 100) for r in yuzde))
    sina("oran satırları PUAN olarak revize ediliyor",
         all(_yakin(r["fark"], r["yeni"] - r["eski"]) for r in puan))
    sina("ima edilen kur revizyon haritasının içinde",
         any(r["kalem"] == "ima_kur" for r in rev),
         "Hattın sorusu odur; haritada olmaması onu görünmez yapardı.")
    sina("iki birim de temsil ediliyor", yuzde and puan)
    sina("figürün seçtiği kalemler ölçülen kalemlerin alt kümesi",
         set(grafik.REV_YUZDE + grafik.REV_PUAN)
         <= ({r["kalem"] for r in metrik.revizyon_olc(
             veri.programlar(),
             veri.program_kodlari(veri.programlar())[0],
             veri.program_kodlari(veri.programlar())[-1])}),
         "Figürde çizilmeyen bir kalem sessizce boş panel bırakırdı.")


def bolum_aylik_ritim() -> None:
    """AYLIK bir bacağın saati AA.YYYY yazılır ve yaşı ayın SON gününden ölçülür.

    09.09.2026'da ölçüldü, iki ayrı yerde aynı kusur. (1) `ozet_uret.olc`
    saati her blokta GG.AA.YYYY yazıyordu; TÜFE serisi ayın İLK gününde
    indeksli olduğu için `tufe_son_tarih` ve `tufe_gecen_yil_tarih`
    "01.08.2026" çıkıyordu — okura o GÜNÜN ölçümü gibi görünen bir aylık
    gözlem. Kural dosyada zaten yazılıydı ama YALNIZ `tufe_tarih`e
    uygulanıyordu. (2) `veri.tazelik_olc` yaşı ham indeksten ölçüyordu; 01.08
    çıpasıyla yaş 15.09'da 45 günlük toleransı aşıyor ve sıradaki TÜFE
    yayımına (03.10) kadar 18 gün SAHTE "bacak gecikti" satırı basılacaktı.
    """
    import datetime as _dt
    import pandas as _pd

    sina("aylık blok AA.YYYY, günlük blok GG.AA.YYYY yazılır",
         ozet_uret.blok_damga("tufe", _dt.date(2026, 8, 1)) == "08.2026"
         and ozet_uret.blok_damga("kur", _dt.date(2026, 9, 8)) == "08.09.2026")
    sina("aylık blok kümesi TÜFE'yi tanıyor", "tufe" in ozet_uret.AYLIK_BLOK)

    _idx = _pd.to_datetime(["2026-06-01", "2026-07-01", "2026-08-01"])
    _T = _pd.DataFrame({"tufe_12a": [1.0, 2.0, 3.0]}, index=_idx)
    _g = _pd.DataFrame({"usdtry": [1.0], "tlref": [1.0]},
                       index=_pd.to_datetime(["2026-09-08"]))
    _taz = veri.tazelik_olc(_g, _g, _T)
    sina("aylık bacağın çıpası ayın SON günü",
         _taz["tufe"]["son"] == "2026-08-31")
    # Sahte alarmın kendisine karşı: eski çıpayla (01.08) 15.09'da yaş 45'i
    # aşardı; yeni çıpayla sıradaki yayım gününde bile toleransın altında.
    _yeni = (_pd.Timestamp("2026-10-03") - _pd.Timestamp("2026-08-31")).days
    _eski = (_pd.Timestamp("2026-09-15") - _pd.Timestamp("2026-08-01")).days
    sina("sağlıklı çevrimde aylık bacak toleransı aşmıyor",
         _yeni < veri.TOLERANS_GUN["tufe"] <= _eski)


def main() -> int:
    print("OVP hattı — duman sınaması (ağa çıkmaz)")
    bolum_ima()
    bolum_yontem()
    bolum_kalan()
    bolum_patika()
    bolum_zincir()
    bolum_carry()
    bolum_tutarlilik()
    bolum_defter()
    bolum_kutu()
    bolum_durdurucu()
    bolum_yapi()
    bolum_okur_dili()
    bolum_cumle()
    bolum_revizyon()
    bolum_aylik_ritim()
    print(f"\n{GECTI} geçti · {DUSTU} düştü")
    if _KUSUR:
        print("Düşenler: " + " | ".join(_KUSUR))
    return 1 if DUSTU else 0


if __name__ == "__main__":
    raise SystemExit(main())
