#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USD/TRY devalüasyon hızı — duman sınaması. Ağa çıkmaz, saniyeler sürer.

`guncelle.py` bu dosyayı hattın ADIMLARINDAN ÖNCE koşturur ve düşerse hat hiç
koşmaz, siteye kopyalama olmaz. Sınama `--denetle` yazan birinin eline
bırakılmaz: zamanlanmış koşu `--denetle` demez ve bozuk bir ölçüm katmanı
çıktısını siteye kopyalamış olurdu.

BURADAKİ HER MADDE BİR ARIZAYA KARŞILIK GELİR — süsleme yok:

 (1) KUR KAYNAĞI. KARAR (09.09.2026, kullanıcı): kurun KONU olduğu her hat
     USD/TRY'yi tek yükleyiciden (ortak/usdtry.py, Yahoo Finance) okur. Bu hat
     kurun konusu olan hattın ta kendisi. Kaynak bir gün sessizce EVDS gösterge
     kuruna dönerse damga VALÖR tarihini taşır (ertesi iş günü) ve tatil öncesi
     yarından ileri bir `_tarih` üretir — yayın kapısı (sayfa sınavı 12) düşer
     ve site donar. Kural yoruma değil KAYNAK METNİNE sorulur.
 (2) KAPANMAMIŞ BAR. Bir ölçüm ancak KAPANMIŞ bir seansı ölçebilir. Kural
     ortak/usdtry'de tek tanım; bu hattın onu KENDİ kopyasıyla atlatmadığı ve
     yükleyicinin bugünün barını gerçekten düşürdüğü sınanır.
 (3) FİGÜR DAMGASI BAĞLAYICI BACAĞI TAŞIR. 09.09.2026'da ölçüldü: Şekil 01–03
     üç bacaklı (kur ve TLREF günlük, banka faizleri haftalık) ve faiz bacağı
     11 gün geride bitiyordu; sayfa üçünü de hattın tek ana saatiyle
     damgalıyordu. Damga artık parçalı ve bacaklar TEK fonksiyondan geliyor.
 (4) BACAK SAATLERİ YAZILIR. `tlref_tarih` ve `faiz_hafta_tarih` olmadan TLREF
     ya da haftalık faiz serisi donsa hiçbir kapı görmezdi: bülten denetiminin
     `karanlik` ölçütü `<anahtar>_tarih` alanlarını sorar ve bu hatta hiç yoktu.
 (5) YAN DOSYA BİRLEŞTİRME. Şekil saat defterini ÜÇ ayrı betik yazıyor; düz bir
     `update` sonuncunun sözlüğünü geçerli kılar ve öbür beş figür defterden
     sessizce düşer (dosya var, okunur, hata vermez).

Koşum:  python3 duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import tempfile
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(BURASI))

import sekil_saat as ss  # noqa: E402

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}" + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


def _ortak(ad: str):
    """`ortak/` modülü — guncelle.py PYTHONPATH'e ekliyor, elle koşuda eklemiyor.
    Hat modüllerinin `_bicim()` yardımcısıyla AYNI yedek yol; sınayanın
    sınanandan başka bir yerden modül bulması ikisinin ayrışması demek olurdu."""
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(KOK / "ortak"))
        return __import__(ad)


# ===========================================================================
# (1) KUR KAYNAĞI — Yahoo, tek yükleyici
# ===========================================================================
def _kur_kaynagi():
    kaynaklar = {}
    for ad in ("evds_ortak.py", "ozet_uret.py", "usdtry_deval_plotly.py",
               "usdtry_weekly_trends.py", "usdtry_monthly_trends.py"):
        kaynaklar[ad] = (BURASI / ad).read_text(encoding="utf-8")

    # Kurun KONUSU olan hat: EVDS kur kodu hiçbir dosyada geçmemeli.
    # (Faiz serileri EVDS'ten gelmeye devam ediyor; yasak yalnız KUR kodları.)
    KUR_KODU = re.compile(r"TP\.DK\.USD|bie_dkdovytl|TP_DK_USD", re.I)
    for ad, src in kaynaklar.items():
        sina(f"{ad}: EVDS kur kodu yok", not KUR_KODU.search(src),
             "kurun konusu olan hat gösterge kuruna dönmüş — valörlü damga geri gelir")

    # Üç çizim betiği ve özet üreticisi kuru AYNI köprüden okur.
    for ad in ("ozet_uret.py", "usdtry_deval_plotly.py",
               "usdtry_weekly_trends.py", "usdtry_monthly_trends.py"):
        sina(f"{ad}: kur `usdtry_serisi` köprüsünden", "usdtry_serisi" in kaynaklar[ad])

    # Köprü ortak yükleyiciye devreder; kendi indirmesini kurmaz.
    e = kaynaklar["evds_ortak.py"]
    sina("evds_ortak: kur ortak/usdtry'ye devredilmiş",
         "_ortak_usdtry()" in e and "import usdtry" in e)
    sina("evds_ortak: kur için yfinance/chart isteği kurulmamış",
         "yfinance" not in e and "finance.yahoo.com" not in e,
         "hat kendi indirmesini kurarsa kapsam ve seviye ölçümü devre dışı kalır")

    u = (KOK / "ortak" / "usdtry.py").read_text(encoding="utf-8")
    sina("ortak/usdtry: kaynak Yahoo Finance", 'SEMBOL = "USDTRY=X"' in u)


# ===========================================================================
# (2) KAPANMAMIŞ BAR — bugünün barı gün kapanmadan seriye girmez
# ===========================================================================
def _kapanmamis_bar():
    m = _ortak("usdtry")
    src = (KOK / "ortak" / "usdtry.py").read_text(encoding="utf-8")
    import pandas as pd

    # Kural GERÇEK fonksiyonla, sahte saatle sınanır: bugünün barı düşer,
    # dünkü seri dokunulmadan kalır.
    simdi = dt.datetime(2026, 9, 9, 11, 0, tzinfo=dt.timezone.utc)
    idx = pd.to_datetime(["2026-09-07", "2026-09-08", "2026-09-09"])
    s = pd.Series([48.1, 48.4, 48.6], index=idx)
    kirp = m.kapanmamis_bari_dusur(s, simdi)
    sina("bugünün barı düşürülüyor",
         len(kirp) == 2 and kirp.index[-1].date() == dt.date(2026, 9, 8),
         f"{list(kirp.index)}")
    tam = m.kapanmamis_bari_dusur(s.iloc[:-1], simdi)
    sina("kapanmış seri kırpılmıyor", len(tam) == 2)

    # Ölçü VAR ama TÜKETİCİSİ yoksa ölçülmemiştir: yükleyici onu çağırıyor mu?
    sina("yükleyici kuralı gerçekten uyguluyor", "kapanmamis_bari_dusur(yeni" in src,
         "fonksiyon var ama seri() çağırmıyorsa kapanmamış bar seriye girer")

    # HAFTA SONU BARI — kapanmamış bar kuralının GÖREMEDİĞİ hâl.
    # 13.09.2026 PAZAR koşusunda gerçekten oldu: 12.09 cumartesi barı
    # "bugün" olmadığı için kapanmamış bar süzgecinden geçti, hattın saati
    # oldu ve sayfa cumartesi damgasıyla yayımlandı. Çerçeve o günün
    # birebir kendisi.
    hafta = pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-12"])
    hs = pd.Series([48.4873, 48.5921, 48.55], index=hafta)
    pazar = dt.datetime(2026, 9, 13, 7, 46, tzinfo=dt.timezone.utc)
    kalan = m.kapanmamis_bari_dusur(hs, pazar)
    sina("cumartesi barını kapanmamış bar kuralı DÜŞÜREMEZ",
         len(kalan) == 3 and kalan.index[-1].date() == dt.date(2026, 9, 12),
         "bu ölçüt, ikinci süzgecin neden gerektiğini sabitler")

    temiz, uyari = m.haftasonu_barini_dusur(kalan)
    sina("cumartesi barı seriye alınmıyor",
         len(temiz) == 2 and temiz.index[-1].date() == dt.date(2026, 9, 11),
         f"{[str(t.date()) for t in temiz.index]}")
    # SİLMEK DEĞİL İŞARETLEMEK: düşen gün adıyla görünmeli.
    sina("düşen gün adıyla uyarıya yazılıyor",
         len(uyari) == 1 and "12.09.2026" in uyari[0],
         f"{uyari}")
    # Hafta içi seri DOKUNULMADAN kalmalı — süzgecin yanlış pozitifi yok.
    ici, bos = m.haftasonu_barini_dusur(hs.iloc[:2])
    sina("hafta içi seri kırpılmıyor, uyarı üretilmiyor",
         len(ici) == 2 and bos == [], f"{len(ici)} · {bos}")

    # Ölçünün TÜKETİCİSİ: seri() çağırıyor mu ve uyarıyı künyeye taşıyor mu?
    sina("yükleyici hafta sonu süzgecini çağırıyor",
         "haftasonu_barini_dusur(yeni)" in src,
         "fonksiyon var ama seri() çağırmıyorsa hafta sonu barı seriye girer")
    sina("hafta sonu uyarısı künyeye ulaşıyor", "uyarilar=hs_uyari" in src,
         "süzgeç sessiz kalırsa gerçek bir damga kayması da sessiz kalır")
    # SIRA: doluluk ölçütü paydası iş günü; hafta sonu barı ondan ÖNCE
    # düşmezse ölçüt kendi paydasıyla kandırılır.
    sina("hafta sonu süzgeci kapsam denetiminden ÖNCE",
         src.index("haftasonu_barini_dusur(yeni)") < src.index("kusur = _kapsam_uyarilari"),
         "sonra gelirse hafta sonu barı hafta içi gözlem sayılır")


# ===========================================================================
# (3) ŞEKİL SAAT DEFTERİ — parçalı damga, tek fonksiyon
# ===========================================================================
def _sekil_saatleri():
    b = _ortak("bicim")
    od = _ortak("okur_dili")
    kur = dt.date(2026, 9, 8)
    tlref = dt.date(2026, 9, 8)
    faiz = dt.date(2026, 8, 28)

    d = ss.sekil_saatleri(kur=kur, tlref=tlref, faiz_hafta=faiz)
    sina("defter hattın BÜTÜN figürlerini kapsıyor", set(d) == set(ss.SEKIL_DOSYALARI),
         f"{set(d) ^ set(ss.SEKIL_DOSYALARI)}")

    # 09.09.2026'da yayımlanmış figürlerden ölçülen hâl.
    beklenen = "kur ve TLREF 08.09.2026 · banka faizi 28.08.2026"
    for dosya in ss.KARMA:
        sina(f"{dosya}: parçalı damga", d[dosya] == beklenen, f"{d[dosya]!r}")
    sina("tek bacaklı figürler çıplak tarih",
         d[ss.SEGMENT] == d[ss.HAFTALIK] == d[ss.AYLIK] == "08.09.2026")

    # BAĞLAYICI BACAK: faiz bacağı geri kalırsa damga onu ADIYLA taşır; bir
    # bacağın gerilemesi öbürünü bayat göstermez, tersi de olmaz.
    d2 = ss.sekil_saatleri(kur=kur, tlref=dt.date(2026, 9, 7), faiz_hafta=faiz)
    sina("üç bacak üç ayrı günde: üçü de damgada",
         d2[ss.DEVAL_1Y] == "kur 08.09.2026 · TLREF 07.09.2026 · banka faizi 28.08.2026",
         f"{d2[ss.DEVAL_1Y]!r}")
    d3 = ss.sekil_saatleri(kur=kur, tlref=kur, faiz_hafta=kur)
    sina("üç bacak aynı günde: damga tek parçaya iner",
         d3[ss.DEVAL_1Y] == "kur, TLREF ve banka faizi 08.09.2026", f"{d3[ss.DEVAL_1Y]!r}")

    # ÖLÇÜLEMEYEN BACAK DAMGADAN DÜŞER (uydurma yok) ama karma figür yine
    # ETİKETLİ kalır: çıplak tarihe düşse `defter_ayir` onu deftere yazar,
    # `damga_…` anahtarı hiç üretilmez ve MDX'in açık anahtarı boşa düşer.
    d4 = ss.sekil_saatleri(kur=kur, tlref=None, faiz_hafta=None)
    sina("çekilemeyen bacak damgada yok", d4[ss.DEVAL_1Y] == "kur 08.09.2026",
         f"{d4[ss.DEVAL_1Y]!r}")
    sina("tek bacak kalsa da karma figür etiketli",
         ss.defter_ayir(d4)[1].get("damga_usdtry_deval") == "kur 08.09.2026",
         "karma figür çıplak tarihe düşüp deftere kaçmamalı — MDX açık anahtar bekler")
    d5 = ss.sekil_saatleri()
    sina("hiçbir bacak ölçülemedi → damga yok, uydurma yok",
         all(v is None for v in d5.values()), f"{d5}")

    # DEFTER ↔ AÇIK ANAHTAR: parçalı damga deftere YAZILAMAZ (sayfa sınavı 18
    # çözemediğini ENGEL sayar), açık anahtara düşer.
    defter, birlesik = ss.defter_ayir(d)
    sina("defter tek tarih ya da None", all(
        v is None or b.tarihe_cevir(v) is not None for v in defter.values()))
    sina("karma figürler defterde None", all(defter[x] is None for x in ss.KARMA))
    sina("parçalı damgalar açık anahtara düştü",
         set(birlesik) == {"damga_" + x.split(".")[0] for x in ss.KARMA}, f"{set(birlesik)}")
    sinir = b.sonraki_is_gunu(dt.date(2026, 9, 9))
    sina("defterdeki hiçbir tarih ertesi iş gününden ileri değil",
         all(v is None or b.tarihe_cevir(v) <= sinir for v in defter.values()))

    # Damga okura basılır: kod ve yapım dili taşımaz, biçim sözleşmesine uyar.
    for v in birlesik.values():
        sina(f"damga okur dilinde: {v[:28]}…", not od.kosu_kaydi_tara([v]),
             f"{od.kosu_kaydi_tara([v])}")
        sina("damga ISO tarih taşımıyor", not re.search(r"\d{4}-\d{2}-\d{2}", v))


# ===========================================================================
# (4) BACAK SAATLERİ ozet.json'a YAZILIR — ölçülemeyen boş, atlanmaz
# ===========================================================================
def _bacak_saatleri():
    src = (BURASI / "usdtry_deval_plotly.py").read_text(encoding="utf-8")
    for anahtar in ("tlref_tarih", "faiz_hafta_tarih"):
        sina(f"{anahtar} çizim betiğinde yazılıyor", f"{anahtar}=" in src)
    sina("ölçülemeyen bacak saati BOŞ yazılır, atlanmaz", src.count('or "—"') == 2,
         "eksik anahtar ile 'bugün ölçülemedi' birbirine benzemez")

    # Bacak saati AYNI yayımdan gelen serilerin EN ESKİ ucudur: en tazesini
    # yazmak geri kalanları olduğundan yeni gösterir.
    import pandas as pd

    def seri(son):
        return pd.Series([1.0], index=pd.to_datetime([son]))
    sina("haftalık bacak saati en eski uçtan",
         ss.bacak_saati(seri("2026-08-28"), seri("2026-08-21"), None) == dt.date(2026, 8, 21))
    sina("hiç seri yoksa bacak saati None", ss.bacak_saati(None, None) is None)
    sina("boş seri ölçüm sayılmaz", ss.seri_sonu(seri("2026-08-28")[0:0]) is None)

    # Yayımlanmış özet: sayfanın çağırdığı anahtarlar gerçekten var mı?
    oz = json.loads((BURASI / "ozet.json").read_text(encoding="utf-8"))
    for anahtar in ("tlref_tarih", "faiz_hafta_tarih", "_sekil_tarih"):
        sina(f"ozet.json {anahtar} taşıyor", anahtar in oz)
    mdx = KOK / "site/src/content/projeler/usdtry-deval.mdx"
    if mdx.exists():
        m = mdx.read_text(encoding="utf-8")
        # AÇIK ANAHTAR: KURALIN ÜRETEBİLECEĞİ bir ad olmalı — ama üretilmemiş
        # olması KUSUR DEĞİLDİR.
        #
        # Eski madde "anahtar özette dizge olarak var" diyordu ve kuralın kendi
        # MEŞRU çıktısını kusur sayıyordu: hiçbir bacak ölçülemediği gün
        # `damga()` None döner (aynı dosyada üç madde yukarıda bunu DOĞRU
        # davranış diye sınıyoruz), `defter_ayir` hiç `damga_*` yazmaz ve madde
        # üç kez düşerdi — duman adımlardan ÖNCE koştuğu için hat komple
        # atlanır, iş akışı kırmızı biter. TÜFEX'in 10.09 arızasının eşi.
        # Üstelik uyarı metni de yanlıştı: o hâlde damga ana saate DÜŞMEZ,
        # çünkü defter figürün girdisini `None` olarak TAŞIR ve bileşen
        # `hasOwnProperty` gördüğü an zinciri keser (GrafikEmbed.astro).
        #
        # Doğru soru üçe bölünür: (a) ad kuralın ürettiği adlardan biri mi,
        # (b) figürün defter girdisi VAR mı — ana saate düşüşü engelleyen tek
        # şey bu, (c) ölçülebilen bir bacak varken anahtar gerçekten yazılmış mı.
        _tum = ss.defter_ayir(ss.sekil_saatleri(
            kur=dt.date(2026, 9, 8), tlref=dt.date(2026, 9, 5),
            faiz_hafta=dt.date(2026, 8, 28)))[1]
        _defter_canli = oz.get("_sekil_tarih") or {}
        for anahtar in re.findall(r'tarihAnahtari="([^"]+)"', m):
            sina(f"MDX `{anahtar}` kuralın ürettiği bir ad", anahtar in _tum,
                 f"kural şunları üretiyor: {sorted(_tum)}")
            _dosya = anahtar.removeprefix("damga_") + ".html"
            sina(f"`{_dosya}` defterde girdi taşıyor (ana saate düşüş yok)",
                 _dosya in _defter_canli,
                 "defterde girdi yoksa bileşen hattın ANA saatini basar")
            if not isinstance(oz.get(anahtar), str):
                # Ölçülemeyen boş bırakılır ve SEBEBİ yazılır — engel değil.
                print(f"    not: `{anahtar}` bu sürümde yazılmamış; o gün hiçbir "
                      "bacak ölçülememiş olabilir (defter girdisi None, sayfa "
                      "o şeklin altına tarih basmaz).")

        # (c) KURALIN İKİ UCU, sahte çerçeveyle: bacak varken anahtar YAZILIR,
        #     hiç bacak yokken YAZILMAZ ve defter girdisi yine de DURUR.
        sina("bacak ölçülebiliyorken MDX'in çağırdığı anahtarlar üretiliyor",
             set(re.findall(r'tarihAnahtari="([^"]+)"', m)) <= set(_tum))
        _bos_defter, _bos_birlesik = ss.defter_ayir(ss.sekil_saatleri())
        sina("hiç bacak yokken damga anahtarı YAZILMIYOR (uydurma yok)",
             not _bos_birlesik, str(_bos_birlesik))
        sina("hiç bacak yokken bile karma figürün defter girdisi DURUYOR "
             "(ana saate düşüş engellenir)",
             all(x in _bos_defter and _bos_defter[x] is None for x in ss.KARMA),
             str(_bos_defter))
        # Tek tarihli figüre açık anahtar KONMAZ: defterle çelişirse sayfa
        # sınavı 18c ENGEL üretir (şeklin alt başlığı ile damga ayrışır).
        for dosya, v in (oz.get("_sekil_tarih") or {}).items():
            if v is None or dosya not in m:
                continue
            i = m.index(dosya)
            sina(f"{dosya}: tek tarihli figürde açık anahtar yok",
                 "tarihAnahtari" not in m[i:m.index("/>", i)])
        for dosya in ss.KARMA:
            if dosya in m:
                i = m.index(dosya)
                sina(f"{dosya}: MDX açık anahtarla çağırıyor",
                     "tarihAnahtari" in m[i:m.index("/>", i)])


# ===========================================================================
# (5) YAN DOSYA BİRLEŞTİRME — defter EZİLMEZ
# ===========================================================================
def _yan_dosya_birlestirme():
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "istatistik_seg.json").write_text(json.dumps(
            {"seg_son_egim": 1.2,
             "_sekil_tarih": {"usdtry_deval_seg.html": "08.09.2026"}}), encoding="utf-8")
        (t / "istatistik_hafta.json").write_text(json.dumps(
            {"hafta_segment": 37,
             "_sekil_tarih": {"usdtry_weekly.html": "08.09.2026"}}), encoding="utf-8")
        (t / "istatistik_ay.json").write_text(json.dumps(
            {"ay_son_ort": 21.6,
             "_sekil_tarih": {"usdtry_monthly.html": "08.09.2026"}}), encoding="utf-8")
        (t / "istatistik_sekil.json").write_text(json.dumps(
            {"tlref_tarih": "08.09.2026", "faiz_hafta_tarih": "28.08.2026",
             "damga_usdtry_deval": "kur 08.09.2026 · banka faizi 28.08.2026",
             "_sekil_tarih": {"usdtry_deval.html": None}}), encoding="utf-8")
        o = ss.yan_dosyalari_birlestir({"_tarih": "08.09.2026"}, str(t))
    sina("üç betiğin defteri BİRLEŞİYOR, ezilmiyor",
         set(o["_sekil_tarih"]) == {"usdtry_deval_seg.html", "usdtry_weekly.html",
                                    "usdtry_monthly.html", "usdtry_deval.html"},
         f"{sorted(o.get('_sekil_tarih', {}))}")
    sina("defter dışı anahtarlar da geldi",
         o.get("tlref_tarih") == "08.09.2026" and o.get("hafta_segment") == 37)
    sina("null girdi korunuyor (ucu ölçülmedi ≠ girdi yok)",
         o["_sekil_tarih"]["usdtry_deval.html"] is None)

    # Eksik yan dosya sessizce atlanır (betik koşmadıysa eski değer düşer),
    # bozuk dosya HATA VERMEZ ama adıyla uyarır.
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "istatistik_ay.json").write_text("{bozuk", encoding="utf-8")
        uyarilar: list[str] = []
        o2 = ss.yan_dosyalari_birlestir({"_tarih": "08.09.2026"}, str(t), uyarilar.append)
    sina("bozuk yan dosya koşuyu düşürmez, adıyla uyarır",
         o2 == {"_tarih": "08.09.2026"} and any("istatistik_ay.json" in u for u in uyarilar),
         f"{uyarilar}")

    # Özet üreticisi bu fonksiyonu GERÇEKTEN çağırıyor mu: ölçü var, tüketici
    # yok kusurunun eşi — birleştirici doğru olsa da çağrılmazsa hiçbir şey
    # değişmez.
    osrc = (BURASI / "ozet_uret.py").read_text(encoding="utf-8")
    sina("ozet_uret birleştiriciyi çağırıyor",
         "sekil_saat.yan_dosyalari_birlestir(ozet, BASE)" in osrc)
    for ad, sabit in (("usdtry_deval_plotly.py", "DEVAL_1Y"),
                      ("usdtry_weekly_trends.py", "HAFTALIK"),
                      ("usdtry_monthly_trends.py", "AYLIK")):
        src = (BURASI / ad).read_text(encoding="utf-8")
        sina(f"{ad}: şekil saatini kendi çizdiği seriden yazıyor",
             "sekil_saat.kayit(" in src and f"sekil_saat.{sabit}" in src)


def main() -> int:
    print("USD/TRY devalüasyon hızı — duman sınaması\n")
    for ad, f in (("Kur kaynağı (Yahoo, tek yükleyici)", _kur_kaynagi),
                  ("Kapanmamış bar", _kapanmamis_bar),
                  ("Şekil saat defteri", _sekil_saatleri),
                  ("Bacak saatleri", _bacak_saatleri),
                  ("Yan dosya birleştirme", _yan_dosya_birlestirme)):
        print(f"\n▶ {ad}")
        f()
    print(f"\n{len(GECTI)} geçti · {len(DUSTU)} düştü")
    for d in DUSTU:
        print(f"  ✗ {d}")
    return 1 if DUSTU else 0


if __name__ == "__main__":
    sys.exit(main())
