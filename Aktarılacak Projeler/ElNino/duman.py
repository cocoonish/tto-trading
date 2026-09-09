#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El Niño hattı — duman sınaması. AĞA ÇIKMAZ, saniyeler sürer, çıkış kodu 0/1.

`guncelle.py` bu dosyayı hattın adımlarından ÖNCE koşturur ve düşerse hat hiç
koşmaz, siteye kopyalama olmaz. Sınama yalnız `--denetle` yazan birinin eline
bırakılsaydı zamanlanmış koşu onu hiç sormaz ve bozuk bir ölçüm katmanı
çıktısını siteye kopyalamış olurdu.

BURADA DURAN HER MADDE BİR ARIZAYA KARŞILIK GELİR (09.09.2026'da ölçüldü)
-------------------------------------------------------------------------
 1. SAAT YAZIMI — özetteki 37 `*_tarih` anahtarının 37'si aylık gözlemi
    "01.08.2026" diye, ayın ilk GÜNÜ gibi yazıyordu. Sözleşme (ortak/bicim =
    lib/bicim) aylık saati `AA.YYYY` ister; tarihi yazan tek yardımcı
    metrik.py'de durur, öbür katmanlar kendi strftime'ını taşımaz.
 2. BACAK SAATLERİ — küresel bloktan türeyen her anahtar emtia ucuyla
    (2026-08) damgalanıyordu; oysa reel seri ABD TÜFE'sine bölünür ve BLS bir
    ay geride (2026-07), Euro Bölgesi HICP sekiz ay geride (2025-12). Her ölçü
    beslendiği serilerin EN ESKİ ucunu taşır.
 3. ŞEKİL SAAT DEFTERİ — dokuz figür dört ritimde ve `_sekil_tarih` yoktu;
    sayfa hepsini hattın tek ana saatiyle damgalıyordu. Defter çizen kodun
    ilanıdır: grafik.py figürün alt yazısına, ozet_uret.py özete AYNI
    fonksiyondan yazar. Kapanmamış aya düşen uç None kalır.
 4. ONI KUYRUĞU — `interpolate(limit=1)` serinin SONUNA da bir ay ekliyordu:
    ONI 2026-06'da biterken tarihçeye 2026-07 için 1,39 girdi (ölçülmemiş
    ay). Yalnız iki gerçek gözlemin arasındaki tek aylık boşluk dolar.
 5. KAYNAK YAŞI — dört küresel kaynak tek damga taşıyordu ve ECB'nin sekiz
    aylık donması hiçbir yerde görünmüyordu. Her kaynağın kendi tarihi, yaşı
    ve hükmü ("güncel" / "N ay geride") yazılır; eşiği aşan koşu kaydına
    okur diliyle düşer. ONI'nin yapısal iki aylık gecikmesi alarm üretmez.
 6. KÜRESEL BLOK DÜŞÜNCE — hat 05–09 numaralı şekilleri kendi klasöründe
    siler ama sitedeki kopyalar kalır (kopya sözleşmesi silmeyi taşımaz).
    Koşu kaydına okura görünür satır yazılır; hangi veriyle çizildiği bir
    önceki özetten okunur.
 7. OKUR DİLİ — koşu kaydı ve özetin cümle alanları sayfaya olduğu gibi
    basılır; sütun adı ("emtia_gida"), ISO tarih ve "12.2025" gibi biçim
    sızıntısı kapıda takılır.
 8. SAYFA SÖZLEŞMESİ — yazının adıyla çağırdığı her anahtar özette var.

SENTETİK ÇERÇEVE ÖLÇÜLEN PENCERELERİ TAŞIR: ONI 1950'den, TÜFE 2005'ten,
Pink Sheet 1960'tan, BIS 1954'ten, ECB 1997'den; uçlar bugünkü ağaçtaki gibi
KADEMELİ (ONI 06 · BLS 07 · ECB 2025-12 · emtia ve BIS 08 · TÜFE 08), çünkü
sınanan şeylerin çoğu tam bu kademeden doğuyor.

Koşum:  python3 duman.py
"""
from __future__ import annotations

import ast
import contextlib
import datetime as dt
import io
import json
import pathlib
import re
import sys
import tempfile
import warnings

import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
BURASI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))

import metrik                                                      # noqa: E402
import kuresel                                                     # noqa: E402
import grafik                                                      # noqa: E402
import ozet_uret                                                   # noqa: E402


def _ortak(ad: str):
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(BURASI.parents[1] / "ortak"))
        return __import__(ad)


bicim = _ortak("bicim")
okur_dili = _ortak("okur_dili")

GECTI, DUSTU = 0, 0
_KUSUR: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    global GECTI, DUSTU
    if kosul:
        GECTI += 1
        print(f"  ✓ {ad}")
    else:
        DUSTU += 1
        _KUSUR.append(ad)
        print(f"  ✗ {ad}" + (f"\n      {ayrinti}" if ayrinti else ""))


# ===========================================================================
#  SENTETİK ÇERÇEVE
# ===========================================================================
BUGUN = dt.date(2026, 9, 9)          # sınama takvime bağlı olmasın
ONI_SON, TUFE_SON = "2026-06", "2026-08"
EMTIA_SON, ABD_SON, EA_SON, FAIZ_SON = "2026-08", "2026-07", "2025-12", "2026-08"
ZIRVELER = ("1983-01", "1997-12", "2015-12", "2023-12")
IC_BOSLUK_TEK = "2010-05"                    # tek aylık iç boşluk → dolar
IC_BOSLUK_CIFT = ("2012-03", "2012-04")      # iki aylık iç boşluk → dolmaz
URUNLER = ("palm", "soya", "pirinc", "bugday", "misir", "seker", "kahve",
           "kakao", "muz", "portakal", "cay")
TOPLU = ("emtia_enerji", "emtia_yakitsiz", "emtia_tarim", "emtia_icecek",
         "emtia_gida", "emtia_yaglar", "emtia_tahil", "emtia_diger",
         "emtia_hammadde", "emtia_gubre", "emtia_metal")


def _oni(son: str = ONI_SON) -> pd.Series:
    idx = pd.date_range("1950-01-01", son, freq="MS")
    rng = np.random.default_rng(1950)
    t = np.arange(len(idx))
    s = pd.Series(np.clip(0.9 * np.sin(2 * np.pi * t / 50) + rng.normal(0, 0.15, len(idx)),
                          -2.0, 1.2), index=idx)
    for z in ZIRVELER:                       # dört güçlü epizot, yedişer ay
        zt = pd.Timestamp(z)
        for k, v in zip(range(-3, 4), (1.6, 1.8, 2.0, 2.3, 2.0, 1.8, 1.6)):
            s[zt + pd.DateOffset(months=k)] = v
    s[pd.Timestamp(IC_BOSLUK_TEK)] = np.nan
    for a in IC_BOSLUK_CIFT:
        s[pd.Timestamp(a)] = np.nan
    return s.round(2)


def _tufe(son: str = TUFE_SON) -> pd.DataFrame:
    idx = pd.date_range("2005-01-01", son, freq="MS")
    rng = np.random.default_rng(2005)
    n = len(idx)
    out = {}
    for i, ad in enumerate(("tufe", "gida", "islenmemis_gida", "islenmis_gida", "cekirdek_c")):
        g = 1.012 + 0.002 * i + rng.normal(0, 0.004, n)
        out[ad] = 100.0 * np.cumprod(g)
    return pd.DataFrame(out, index=idx).round(4)


def _kuresel(emtia_son=EMTIA_SON, abd_son=ABD_SON, ea_son=EA_SON,
             faiz_son=FAIZ_SON) -> pd.DataFrame:
    idx = pd.date_range("1954-07-01", max(emtia_son, abd_son, faiz_son), freq="MS")
    rng = np.random.default_rng(1954)
    K = pd.DataFrame(index=idx)

    def dilim(bas, son, n_ad, seed, taban, adim):
        i = pd.date_range(bas, son, freq="MS")
        r = np.random.default_rng(seed)
        return pd.Series(taban * np.cumprod(1 + r.normal(adim, 0.03, len(i))), index=i)

    for j, ad in enumerate(TOPLU + URUNLER):
        K[ad] = dilim("1960-01-01", emtia_son, ad, 100 + j, 50.0 + j, 0.002)
    for j, ad in enumerate(("abd_tufe", "abd_gida", "abd_cekirdek")):
        i = pd.date_range("1960-01-01", abd_son, freq="MS")
        K[ad] = pd.Series(30.0 * np.cumprod(1 + rng.normal(0.003 + 0.0002 * j, 0.002, len(i))), index=i)
    i = pd.date_range("1954-07-01", faiz_son, freq="MS")
    K["faiz_abd"] = pd.Series(np.clip(4 + 3 * np.sin(np.arange(len(i)) / 40) + rng.normal(0, 0.1, len(i)), 0, None), index=i)
    i = pd.date_range("2002-02-01", "2026-07-01", freq="MS")
    K["faiz_tr"] = pd.Series(20 + 15 * np.sin(np.arange(len(i)) / 30), index=i)
    i = pd.date_range("1999-01-01", faiz_son, freq="MS")
    K["faiz_ea"] = pd.Series(np.clip(2 + 2 * np.sin(np.arange(len(i)) / 40), 0, None), index=i)
    i = pd.date_range("1997-01-01", ea_son, freq="MS")
    K["ea_tufe_12a"] = pd.Series(2.0 + rng.normal(0, 0.6, len(i)), index=i)
    K["ea_gida_12a"] = pd.Series(2.4 + rng.normal(0, 0.9, len(i)), index=i)
    return K.round(4)


def _yaz_cerceve(data: pathlib.Path, kuresel_var: bool = True, **uclar) -> None:
    data.mkdir(parents=True, exist_ok=True)
    _oni(uclar.get("oni_son", ONI_SON)).to_frame("oni").to_csv(data / "oni.csv")
    _tufe(uclar.get("tufe_son", TUFE_SON)).to_csv(data / "tufe.csv")
    yol = data / "kuresel.csv"
    if kuresel_var:
        _kuresel(**{k: v for k, v in uclar.items()
                    if k in ("emtia_son", "abd_son", "ea_son", "faiz_son")}).to_csv(yol)
    elif yol.exists():
        yol.unlink()


def _kos(tmp: pathlib.Path, kuresel_var: bool = True, **uclar) -> dict:
    """Hattın ağsız zincirini (ölçüm → küresel → çizim → özet) GERÇEK giriş
    noktalarından koşturur; yalnız yollar geçici dizine çevrilir."""
    data, cikti, site = tmp / "data", tmp / "cikti", tmp / "site"
    _yaz_cerceve(data, kuresel_var, **uclar)
    cikti.mkdir(exist_ok=True)
    metrik.DATA = kuresel.DATA = grafik.DATA = ozet_uret.DATA = data
    grafik.CIKTI = cikti
    ozet_uret.HEDEF = site
    metrik._UYARI.clear()
    kuresel._UYARI.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        metrik.main()
        kuresel.main()
        grafik.main()
        ozet_uret.main()
    M = json.loads((data / "metrik.json").read_text(encoding="utf-8"))
    G = (json.loads((data / "kuresel.json").read_text(encoding="utf-8"))
         if (data / "kuresel.json").exists() else None)
    O = json.loads((site / "ozet.json").read_text(encoding="utf-8"))
    U = json.loads((site / "uyarilar.json").read_text(encoding="utf-8"))
    return {"M": M, "G": G, "O": O, "U": U,
            "cikti": sorted(p.name for p in cikti.glob("*.html")),
            "html": {p.name: p.read_text(encoding="utf-8") for p in cikti.glob("*.html")}}


def _saatler(O: dict) -> dict[str, str | None]:
    return {k: v for k, v in O.items() if k.endswith("_tarih") and k != "_sekil_tarih"}


def _kaynak(ad: str) -> str:
    return (BURASI / ad).read_text(encoding="utf-8")


# ===========================================================================
#  BÖLÜMLER
# ===========================================================================
def bolum_saat_yazimi(R: dict) -> None:
    print("\n▶ 1. Saat yazımı (AA.YYYY, tek yardımcı)")
    O = R["O"]
    s = _saatler(O)
    sina("ana saat `_tarih` aylık yazımda (TÜFE ayı)", O.get("_tarih") == "08.2026",
         f"_tarih = {O.get('_tarih')!r}")
    gun = {k: v for k, v in s.items() if isinstance(v, str) and re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", v)}
    sina("hiçbir aylık saat gün yazımıyla değil (eski kusur: 01.08.2026)", not gun,
         f"{len(gun)} anahtar: {sorted(gun)[:5]}")
    kotu = {k: v for k, v in s.items()
            if not (v is None or (isinstance(v, str) and re.fullmatch(r"\d{2}\.\d{4}", v)))}
    sina("her saat anahtarı AA.YYYY ya da None", not kotu, f"{sorted(kotu.items())[:5]}")
    cozulmeyen = [k for k, v in s.items() if v and bicim.tarihe_cevir(v) is None]
    sina("her saat ortak/bicim ile çözülüyor", not cozulmeyen, f"{cozulmeyen[:5]}")
    sinir = bicim.sonraki_is_gunu(BUGUN)
    ileri = [k for k, v in s.items() if v and bicim.tarihe_cevir(v) > sinir]
    sina("hiçbir saat ertesi iş gününden ileri değil", not ileri, f"{ileri[:5]}")
    # HER ÖLÇÜNÜN SAATİ VAR: kapsam sözleşmeden — sayısal her anahtar (sabitler
    # ve yaş sayaçları hariç) `<anahtar>_tarih` taşır. Aksi hâlde o anahtar
    # hattın ana saatine düşer ve bacak kusuru sessizce geri gelir.
    SABIT = {"esik", "asgari_ay", "ufuk", "emtia_yas_ay"}
    saatsiz = [k for k, v in O.items()
               if isinstance(v, (int, float)) and not isinstance(v, bool)
               and k not in SABIT and not k.endswith("_yas_ay")
               and not k.endswith("_tarih") and f"{k}_tarih" not in O]
    sina("sayısal her ölçünün kendi saati var (sabitler hariç)", not saatsiz,
         f"{len(saatsiz)} saatsiz: {saatsiz[:6]}")
    sina("`_ay`, `oni_son_ay`, `emtia_son` etiketleri saat anahtarı DEĞİL (ISO kalır)",
         O.get("_ay") == "2026-08" and O.get("oni_son_ay") == "2026-06"
         and O.get("emtia_son") == "2026-08" and O.get("oni_son_ad") == "Haziran 2026")
    # Tek yardımcı: tarihi yazan strftime kalıbı yalnız metrik.py'nin
    # yardımcılarında; kuresel/grafik/ozet_uret kendi kalıbını taşımaz.
    for ad in ("kuresel.py", "ozet_uret.py", "grafik.py"):
        src = _kaynak(ad)
        sina(f"{ad} tarihi kendisi yazmıyor (%d.%m.%Y / %m.%Y yok)",
             "%d.%m.%Y" not in src and "%m.%Y" not in src)
    sina("metrik.py: gün yazımı yalnız gun_damga içinde",
         _kaynak("metrik.py").count("%d.%m.%Y") == 1)


def bolum_bacak(R: dict) -> None:
    print("\n▶ 2. Bacak saatleri (en eski uç bağlar)")
    O = R["O"]
    beklenen = {
        "oni_son_tarih": "06.2026",            # ONI'nin kendi ucu
        "gida_12a_tarih": "08.2026",           # TÜFE
        "tr_cekirdek_beta_tarih": "08.2026",   # yalnız TÜFE
        "abd_gida_12a_tarih": "07.2026",       # BLS
        "abd_cekirdek_beta_tarih": "07.2026",
        "ea_gida_son_tarih": "12.2025",        # ECB (donmuş)
        "gecis_yillik_ea_beta_tarih": "12.2025",
        "reel_gida_son_tarih": "07.2026",      # emtia ÷ ABD TÜFE: deflatör bağlar
        "nominal_gida_son_tarih": "08.2026",   # yalnız emtia
        "gor_emtia_son_tarih": "08.2026",      # gıda − metal, ikisi de Pink Sheet
        "fed_kosulsuz_18ay_tarih": "08.2026",  # yalnız BIS
        "fed_olculen_tarih": "06.2026",        # epizotlar ONI'den
        "gecis_tr_beta_tarih": "07.2026",      # reel emtia (07) ↔ TÜFE (08)
        "gecis_abd_beta_tarih": "07.2026",
        "kur_fark_tarih": "06.2026",           # epizot çalışması: ONI bağlar
        "kir_kakao_fark_tarih": "06.2026",
        "kirilim_tepe_fark_tarih": "06.2026",
        "hukum_tarih": "06.2026",
    }
    for k, v in beklenen.items():
        sina(f"{k} = {v}", O.get(k) == v, f"özet: {O.get(k)!r}")
    ea = {k: v for k, v in _saatler(O).items() if k.startswith("ea_")}
    sina("Euro Bölgesi anahtarlarının HİÇBİRİ hattın saatini taşımıyor (eski kusur)",
         ea and all(v == "12.2025" for v in ea.values()), f"{ea}")
    sina("blok ana saati en yeni bacak (kuresel_tarih = 08.2026)", O.get("kuresel_tarih") == "08.2026")


def bolum_defter(R: dict, tmp: pathlib.Path) -> None:
    print("\n▶ 3. Şekil saat defteri (`_sekil_tarih`)")
    O, M, G = R["O"], R["M"], R["G"]
    d = O.get("_sekil_tarih") or {}
    sina("defter dokuz figürün hepsini taşıyor", set(d) == set(R["cikti"]) and len(d) == 9,
         f"defter {sorted(d)} · çıktı {R['cikti']}")
    for ad in ("01-oni-tarihce.html", "02-oni-goreceli-gida.html", "03-gecikme-profili.html",
               "04-epizot.html", "05-kuresel-gida.html", "06-urun-kirilimi.html",
               "07-uc-olcek.html", "08-fed-patikasi.html"):
        sina(f"{ad} → 06.2026 (ONI en eski bacak)", d.get(ad) == "06.2026", f"{d.get(ad)!r}")
    sina("09-gecis-profili.html → 07.2026 (ONI çizilmez; reel emtia bağlar)",
         d.get("09-gecis-profili.html") == "07.2026", f"{d.get('09-gecis-profili.html')!r}")
    sina("defterdeki her damga çözülüyor ve ileri değil",
         all(v is None or (bicim.tarihe_cevir(v) is not None
                           and bicim.tarihe_cevir(v) <= bicim.sonraki_is_gunu(BUGUN))
             for v in d.values()))
    # ÇİZEN KODUN İLANI: figürün kendi alt yazısındaki damga ile özet aynı
    # fonksiyondan; her HTML "Veri ucu: <ay adı>" satırını taşıyor.
    uzun = metrik.sekil_saatleri(M, G, uzun=True, bugun=BUGUN)
    eksik = [ad for ad, h in R["html"].items()
             if uzun.get(ad) and f"Veri ucu: {uzun[ad]}." not in h]
    sina("her figürün alt yazısı kendi veri ucunu taşıyor", not eksik, f"{eksik}")
    sina("grafik.SAAT defteri = metrik.sekil_saatleri (tek kaynak)", grafik.SAAT == uzun)
    sina("uzun yazım okur etiketi (Haziran 2026 / Temmuz 2026)",
         uzun.get("01-oni-tarihce.html") == "Haziran 2026"
         and uzun.get("09-gecis-profili.html") == "Temmuz 2026")
    # AÇIK AY: ONI ucu içinde bulunulan aya düşerse damga yarına düşer ve
    # yayın kapısı ENGEL üretir (OVP hattında ölçüldü); uç None kalır.
    acik = metrik.sekil_saatleri(M, G, bugun=dt.date(2026, 6, 15))
    sina("kapanmamış aya düşen uç None (ölçülmemiş gün ilan edilmez)",
         acik.get("01-oni-tarihce.html") is None and acik.get("09-gecis-profili.html") is None)
    kapali = metrik.sekil_saatleri(M, G, bugun=dt.date(2026, 7, 1))
    sina("ay kapandığı gün damga kendiliğinden gelir",
         kapali.get("01-oni-tarihce.html") == "06.2026")
    for ad in ("grafik.py", "ozet_uret.py"):
        sina(f"{ad} defteri metrik.sekil_saatleri'nden okuyor", "sekil_saatleri(" in _kaynak(ad))


def bolum_oni(R: dict) -> None:
    print("\n▶ 4. ONI kuyruğu doldurulmaz")
    M = R["M"]
    t = {k["ay"]: k["oni"] for k in M["tarihce"]}
    sina("tarihçede ONI'nin ötesindeki iki ay boş (2026-07, 2026-08)",
         t.get("2026-07") is None and t.get("2026-08") is None,
         f"2026-07={t.get('2026-07')!r} 2026-08={t.get('2026-08')!r}")
    beklenen = round(float(_oni().dropna().iloc[-1]), 2)
    sina("ONI'nin son ölçümü gerçek ucu (2026-06), kendi saati 06.2026, değeri doldurulmamış",
         M.get("oni_son_ay") == "2026-06" and M.get("oni_son_tarih") == "06.2026"
         and M.get("oni_son") == beklenen,
         f"{M.get('oni_son_ay')} {M.get('oni_son_tarih')} {M.get('oni_son')} ≠ {beklenen}")
    sina("tek aylık İÇ boşluk dolar", t.get(IC_BOSLUK_TEK) is not None)
    # `limit=1` pandas'ta "her boşluğun en çok BİR ayı" demektir (ölçüldü:
    # iki aylık boşluğun ilk ayı doluyor, ikincisi boş kalıyor); sınanan şey
    # sınırsız doldurmaya geri dönülmemesi — boşluğun tamamı dolmamalı.
    sina("iki aylık iç boşluk tümüyle dolmaz (limit 1: en çok bir ay)",
         any(t.get(a) is None for a in IC_BOSLUK_CIFT),
         f"{[t.get(a) for a in IC_BOSLUK_CIFT]}")
    for ad in ("metrik.py", "kuresel.py"):
        src = _kaynak(ad)
        n = src.count(".interpolate(")
        sina(f"{ad}: her interpolate çağrısı limit_area=\"inside\" taşıyor",
             n >= 1 and src.count('limit_area="inside"') == n, f"{n} çağrı")
    G = R["G"]
    sina("küresel gecikme profili NaN kuyrukla da kuruluyor", bool(G and G.get("kur_capraz")))


def bolum_kaynak(R: dict) -> None:
    print("\n▶ 5. Kaynak yaşı ve koşu kaydı")
    O, U = R["O"], R["U"]
    sina("altı kaynağın kendi tarihi var",
         all(f"kaynak_{k}_tarih" in O for k in ("oni", "tufe", "pink", "bls", "bis", "ecb")))
    sina("ECB: 12.2025 · 8 ay geride · hüküm '8 ay geride'",
         O.get("kaynak_ecb_tarih") == "12.2025" and O.get("kaynak_ecb_yas_ay") == 8
         and O.get("kaynak_ecb_durum") == "8 ay geride",
         f"{O.get('kaynak_ecb_tarih')} {O.get('kaynak_ecb_yas_ay')} {O.get('kaynak_ecb_durum')}")
    sina("BLS bir ay geride → güncel; Pink Sheet ve BIS → güncel",
         O.get("kaynak_bls_durum") == "güncel" and O.get("kaynak_bls_yas_ay") == 1
         and O.get("kaynak_pink_durum") == "güncel" and O.get("kaynak_bis_durum") == "güncel")
    sina("ONI'nin yapısal iki aylık gecikmesi alarm üretmez",
         O.get("kaynak_oni_yas_ay") == 2 and O.get("kaynak_oni_durum") == "güncel")
    sina("kapsam etiketi okur yazımında (Ocak 1997 → Aralık 2025)",
         O.get("kaynak_ecb_kapsam") == "Ocak 1997 → Aralık 2025", f"{O.get('kaynak_ecb_kapsam')!r}")
    sat = U.get("uyarilar") or []
    ecb = [x for x in sat if "Euro Bölgesi HICP" in x and "8 ay" in x and "Aralık 2025" in x]
    sina("koşu kaydında ECB donması okur diliyle yazılı", len(ecb) == 1, f"{sat}")
    sina("güncel kaynaklar için satır yok", not [x for x in sat if "BLS" in x or "NOAA" in x])
    sina("uyarilar.json: koşu günü GG.AA.YYYY, veri AA.YYYY, durum 'ölçüldü'",
         re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", U.get("kosum") or "") is not None
         and U.get("veri") == "08.2026" and U.get("kuresel_durum") == "ölçüldü")


def bolum_kuresel_yok(tmp: pathlib.Path) -> None:
    print("\n▶ 6. Küresel blok düştüğünde")
    # Aynı dizinde önce tam koşu (küresel çıktılar ve önceki özet oluşsun),
    # sonra kuresel.csv'siz koşu.
    _kos(tmp, kuresel_var=True)
    R = _kos(tmp, kuresel_var=False)
    O, U = R["O"], R["U"]
    sina("kuresel.json silindi, özet küresel anahtar taşımıyor",
         R["G"] is None and "kur_fark" not in O and "ea_fark" not in O)
    sina("hattın klasöründe yalnız 01–04 kaldı",
         R["cikti"] == ["01-oni-tarihce.html", "02-oni-goreceli-gida.html",
                        "03-gecikme-profili.html", "04-epizot.html"], f"{R['cikti']}")
    sina("defter yalnız Türkiye figürlerini taşıyor",
         set(O.get("_sekil_tarih") or {}) == set(R["cikti"]))
    sina("kuresel_durum = ölçülemedi", O.get("kuresel_durum") == "ölçülemedi"
         and U.get("kuresel_durum") == "ölçülemedi")
    sat = U.get("uyarilar") or []
    satir = [x for x in sat if "05–09" in x and "önceki koşudan" in x]
    sina("koşu kaydında okura görünür satır: 05–09 sitede önceki koşudan",
         len(satir) == 1, f"{sat}")
    sina("satır önceki özetin küresel ayını adıyla söylüyor (Ağustos 2026)",
         bool(satir) and "Ağustos 2026 verisiyle" in satir[0], f"{satir}")
    sina("Türkiye ölçümü ayakta (ana saat ve TÜFE anahtarları)",
         O.get("_tarih") == "08.2026" and "gida_12a" in O and "oni_son" in O)
    # Önceki özet yokken de satır kurulur (ay bilinmez, uydurulmaz).
    s0 = ozet_uret.kuresel_yok_satiri(None)
    sina("önceki özet yoksa ay yazılmaz, satır yine kurulur",
         "05–09" in s0 and "verisiyle" not in s0)
    _okur_dili(R, "küresel yokken")


def _okur_dili(R: dict, etiket: str) -> None:
    O, U = R["O"], R["U"]
    sat = [("uyarilar", x) for x in (U.get("uyarilar") or [])]
    sat += [(a, m) for a, m in okur_dili.ozet_cumleleri(O)]
    bulgu = [(a, b) for a, m in sat for b in okur_dili.kosu_kaydi_tara([m])]
    engel = [x for x in bulgu if x[1][1] in okur_dili.KOSU_KAYDI_ENGEL]
    sina(f"okur dili ({etiket}): koşu kaydı ve özet cümlelerinde ENGEL yok",
         not engel, f"{engel[:4]}")
    sina(f"okur dili ({etiket}): anahtar adı ve biçim sızıntısı da yok",
         not bulgu, f"{bulgu[:4]}")
    sina(f"okur dili ({etiket}): kapsam boş değil", len(sat) >= 3, f"{len(sat)} satır")


def bolum_okur_dili(R: dict) -> None:
    print("\n▶ 7. Okur dili")
    _okur_dili(R, "küresel varken")
    # Kırılım uyarıları sütun adıyla değil ürünün adıyla yazılır: eksik bir
    # ürün serisini sentetik tabloyla kurup satırı sorar.
    with tempfile.TemporaryDirectory() as t2:
        t2 = pathlib.Path(t2)
        R2 = _kos(t2)
        K = pd.read_csv(t2 / "data" / "kuresel.csv", index_col=0, parse_dates=True)
        K.drop(columns=["kakao"]).to_csv(t2 / "data" / "kuresel.csv")
        kuresel._UYARI.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            kuresel.main()
            ozet_uret.main()
        U = json.loads((t2 / "site" / "uyarilar.json").read_text(encoding="utf-8"))
        s = [x for x in U["uyarilar"] if "Kakao" in x]
        sina("eksik ürün serisi koşu kaydına ürün ADIYLA düşer (sütun adı değil)",
             len(s) == 1 and "kakao" not in s[0].replace("Kakao", ""), f"{U['uyarilar']}")
        sina("eksik ürün satırı okur dili kapısından geçiyor",
             not okur_dili.kosu_kaydi_tara(s), f"{okur_dili.kosu_kaydi_tara(s)}")
        del R2


def bolum_sayfa(R: dict) -> None:
    print("\n▶ 8. Sayfa sözleşmesi ve yapısal kilitler")
    O = R["O"]
    mdx = BURASI.parents[1] / "site" / "src" / "content" / "analiz" / "el-nino-enflasyon-2026-08-31.mdx"
    if mdx.exists():
        kul = set(re.findall(r'<Deger proje="el-nino" anahtar="([^"]+)"',
                             mdx.read_text(encoding="utf-8")))
        eksik = sorted(kul - set(O))
        sina(f"yazının adıyla çağırdığı {len(kul)} anahtarın hepsi özette", not eksik, f"{eksik[:8]}")
    else:
        print("  – yazı dosyası yok, anahtar sözleşmesi atlandı")
    # `if __name__` kapısının altında tanım yok (derlenir, içe aktarılır, ama
    # betik olarak koşarken NameError — bu depoda bir kez ölçüldü).
    for ad in ("metrik.py", "kuresel.py", "grafik.py", "ozet_uret.py"):
        agac = ast.parse(_kaynak(ad))
        kapi = next((i for i, n in enumerate(agac.body)
                     if isinstance(n, ast.If) and "__name__" in ast.dump(n.test)), None)
        sonra = [n for n in agac.body[kapi + 1:]] if kapi is not None else []
        sina(f"{ad}: kapıdan sonra tanım yok",
             not any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) for n in sonra))
    sina("kuresel.py her ölçüyü saatiyle koyuyor (koy) ve defteri yazıyor (saatleri_yaz)",
         "koy(" in _kaynak("kuresel.py") and "saatleri_yaz(" in _kaynak("kuresel.py"))
    sina("kaynak listesi tek yerde (metrik.KAYNAK_AD altı kaynak)",
         set(metrik.KAYNAK_AD) == {"oni", "tufe", "pink", "bls", "bis", "ecb"})


def main() -> int:
    print("El Niño hattı — duman sınaması")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        R = _kos(tmp)
        bolum_saat_yazimi(R)
        bolum_bacak(R)
        bolum_defter(R, tmp)
        bolum_oni(R)
        bolum_kaynak(R)
        bolum_okur_dili(R)
        bolum_sayfa(R)
    with tempfile.TemporaryDirectory() as tmp2:
        bolum_kuresel_yok(pathlib.Path(tmp2))
    print(f"\n  {GECTI} geçti · {DUSTU} DÜŞTÜ")
    if _KUSUR:
        for k in _KUSUR:
            print(f"    ✗ {k}")
    return 1 if DUSTU else 0


if __name__ == "__main__":
    raise SystemExit(main())
