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
    # Özetin değeri ve etiketi AYNI çekimden: iki ayrı seri() çağrısı iki
    # ayrı çekimdir (birincisi yedek yola düşüp ikincisi saatlik barı alırsa
    # kart Londra gece yarısı değerini "İstanbul 18:00" diye basardı).
    o = kaynaklar["ozet_uret.py"]
    sina("ozet_uret: seri ve künye tek çekimden", o.count("usdtry_serisi_kunye(") == 1
         and "usdtry_kunye(" not in o and "usdtry_serisi(" not in o,
         "seri ile künye ayrı çağrılarla kuruluyor")
    import evds_ortak as _eo
    sayac = []
    class _Sahte:
        @staticmethod
        def seri(bas=None, onbellek=None):
            import pandas as pd
            sayac.append(bas)
            return type("K", (), {"seri": pd.Series([49.0], index=pd.to_datetime(["2026-10-01"])),
                                  "uyarilar": []})()
        @staticmethod
        def kunye(k):
            return {"kur_son": "01.10.2026", "kur_kapanis": "İstanbul 18:00"}
    _eski = _eo._ortak_usdtry
    try:
        _eo._ortak_usdtry = lambda: _Sahte
        s_, kn_ = _eo.usdtry_serisi_kunye("2026-06-01", uyar=lambda *_: None)
    finally:
        _eo._ortak_usdtry = _eski
    sina("köprü: seri ve künye tek seri() çağrısından", len(sayac) == 1 and kn_["kur_son"] == "01.10.2026"
         and s_.name == "USDTRY=X", f"çağrı {len(sayac)}")

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
    sina("hafta sonu uyarısı künyeye ulaşıyor", "list(hs_uyari)" in src and "uyarilar=uyarilar" in src,
         "süzgeç sessiz kalırsa gerçek bir damga kayması da sessiz kalır")
    # SIRA: doluluk ölçütü paydası iş günü; hafta sonu barı ondan ÖNCE
    # düşmezse ölçüt kendi paydasıyla kandırılır.
    sina("hafta sonu süzgeci kapsam denetiminden ÖNCE",
         src.index("haftasonu_barini_dusur(yeni)") < src.index("kusur = _kapsam_uyarilari"),
         "sonra gelirse hafta sonu barı hafta içi gözlem sayılır")


# ===========================================================================
# (2b) KAPANIŞ ANI — İstanbul 18:00, saatlik bardan (karar 02.10.2026)
# ===========================================================================
def _kapanis_ani():
    """Yahoo'nun kapanmış günlük döviz barının kapanış alanı günün BAŞIDIR;
    seri saatlik bardan İstanbul 18:00'de kurulur. Çerçeve 02.10.2026'nın
    birebir yapısı (sentetik fiyatlarla): İstanbul seansı düz, akşam ve gece
    saatlerinde sığ kotasyon sıçramaları."""
    f = _ortak("fx_kapanis")
    m = _ortak("usdtry")
    import pandas as pd
    import numpy as np
    saat = pd.date_range("2026-09-28 00:00", "2026-10-02 06:00", freq="1h", tz="UTC")
    saat = saat[saat.dayofweek < 5]
    fiyat = pd.Series(49.0, index=saat)
    for g in pd.date_range("2026-09-28", "2026-10-01", tz="UTC"):
        gun = (g - pd.Timestamp("2026-09-28", tz="UTC")).days
        fiyat[(saat >= g) & (saat < g + pd.Timedelta(hours=15))] = 49.0 + 0.01 * gun     # İstanbul seansı
        fiyat[(saat >= g + pd.Timedelta(hours=15)) & (saat < g + pd.Timedelta(hours=24))] = 49.2 + 0.01 * gun  # gece
    # 02.10 sabahı her saat ayrı fiyat: canlı kotasyon ölçüm anında BAŞLAMIŞ
    # son barın fiyatı olmalı (04:00 barı), sonraki barlar onu belirleyemez.
    bugun_saat = fiyat.index >= pd.Timestamp("2026-10-02", tz="UTC")
    fiyat[bugun_saat] = [49.10 + 0.01 * t.hour for t in fiyat.index[bugun_saat]]
    sabah = dt.datetime(2026, 10, 2, 4, 18, tzinfo=dt.timezone.utc)
    k = f.saatlik_kapanislar(fiyat, "tr", sabah)
    sina("kapanış İstanbul 18:00'deki son saatlik bar", abs(float(k.seri.iloc[-1]) - 49.03) < 1e-9
         and k.seri.index[-1].date() == dt.date(2026, 10, 1), f"{k.seri.tail(2).to_dict()}")
    sina("gece kotasyonu kapanışa girmiyor", all(v < 49.1 for v in k.seri.values), f"{k.seri.to_dict()}")
    sina("kapanış anı 15:00 UTC olarak kayıtlı", k.kapanis_utc.get("2026-10-01") == "2026-10-01T15:00:00Z",
         f"{k.kapanis_utc}")
    sina("canlı kotasyon ölçüm anının son fiyatı, kapanışa karışmıyor",
         k.canli is not None and abs(k.canli[1] - 49.14) < 1e-9 and k.canli[0] == "2026-10-02T04:18:00Z",
         f"{k.canli}")
    # Kotasyonun damgası barın KENDİ saatidir; son bar 90 dakikadan eskiyse
    # (besleme durdu, piyasa kapalı) kotasyon hiç basılmaz — pazar öğleden
    # sonrası cuma akşamının fiyatını "şimdi" diye göstermesin.
    k_ = f.saatlik_kapanislar(fiyat, "tr", dt.datetime(2026, 10, 2, 7, 20, tzinfo=dt.timezone.utc))
    sina("kapanmış son barın kotasyonu barın kapanış saatiyle damgalanır",
         k_.canli is not None and k_.canli[0] == "2026-10-02T07:00:00Z", f"{k_.canli}")
    k_ = f.saatlik_kapanislar(fiyat, "tr", dt.datetime(2026, 10, 4, 14, 3, tzinfo=dt.timezone.utc))
    sina("son bar 90 dakikadan eskiyse canlı kotasyon yok", k_.canli is None, f"{k_.canli}")
    ogle = dt.datetime(2026, 10, 1, 14, 30, tzinfo=dt.timezone.utc)
    k2 = f.saatlik_kapanislar(fiyat, "tr", ogle)
    sina("kapanış anı gelmemiş gün seriye girmiyor", k2.seri.index[-1].date() == dt.date(2026, 9, 30),
         f"{k2.seri.index[-1]}")
    sina("hafta sonu günü üretilmiyor", all(t.dayofweek < 5 for t in k.seri.index))
    # Kaynağın tek tük hafta sonu barı (Yahoo bazen cumartesi öğleden sonrasına
    # bir kotasyon yazar) cumartesinin İstanbul penceresine düşer ve kapanış
    # anına bir saat kala kapanır: hafta içi kuralı olmasa cumartesi "kapanış"
    # diye basılırdı. Besleme boşluğu sınaması bunu YAKALAMAZ (bar yakın).
    cuma = pd.date_range("2026-10-02 00:00", "2026-10-02 20:00", freq="1h", tz="UTC")
    hs = pd.concat([pd.Series(49.05, index=cuma),
                    pd.Series(49.30, index=pd.DatetimeIndex(["2026-10-03 13:00"], tz="UTC"))])
    k4 = f.saatlik_kapanislar(hs, "tr", dt.datetime(2026, 10, 3, 16, 0, tzinfo=dt.timezone.utc))
    sina("hafta sonu barı cumartesi kapanışı üretmiyor",
         pd.Timestamp("2026-10-03") not in k4.seri.index and "2026-10-03" not in k4.olculemeyen
         and pd.Timestamp("2026-10-02") in k4.seri.index, f"{k4.seri.to_dict()} {k4.olculemeyen}")
    # Besleme sabah kesildiyse o gün "kapanış" diye sabah fiyatı basılmaz.
    kes = fiyat[~((fiyat.index >= "2026-09-30 06:00") & (fiyat.index < "2026-09-30 23:00"))]
    k3 = f.saatlik_kapanislar(kes, "tr", sabah)
    sina("kapanış anına yetişmeyen gün ölçülemez sayılıyor",
         "2026-09-30" in k3.olculemeyen and pd.Timestamp("2026-09-30") not in k3.seri.index,
         f"{k3.olculemeyen}")
    # Günlük bar: kapanış alanı günün başıdır → değer önceki hafta içi güne,
    # YALNIZ bar o günün ertesi günüyse. Pazartesi barının başı hafta sonu
    # açılışından sonradır: cumartesi barı olmayan cuma ölçülemez (03.10.2026;
    # bulut keşfi #317, G10'da medyan 7,4 bp sapma). Bu madde eskiden TAM TERSİNİ
    # sınıyordu — "05.10 pazartesi barı → 02.10 cuma" — yani kusuru kural diye
    # koruyordu. Fikstür iki haftayı birden taşır: cumartesi barı olan ve olmayan.
    gunluk = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
                       index=pd.to_datetime(["2026-09-24", "2026-09-25", "2026-09-26", "2026-09-28",
                                             "2026-09-29", "2026-10-02", "2026-10-05"]))
    d = f.gunluk_duzelt(gunluk)
    sina("günlük barın değeri bir önceki hafta içi güne yazılıyor; cumartesi barı olmayan cuma ölçülemez",
         [str(t.date()) for t in d.index] == ["2026-09-23", "2026-09-24", "2026-09-25", "2026-09-28", "2026-10-01"]
         and list(d.values) == [1.0, 2.0, 3.0, 5.0, 6.0] and d.attrs.get("olculemeyen") == ["2026-10-02"],
         f"{d.to_dict()} {d.attrs}")
    cmt = pd.Series([5.0, 6.0], index=pd.to_datetime(["2026-10-03", "2026-10-05"]))
    sina("cumartesi barı cumanın değeridir, pazartesi barı değildir",
         float(f.gunluk_duzelt(cmt).loc["2026-10-02"]) == 5.0, f"{f.gunluk_duzelt(cmt).to_dict()}")
    # Yükleyici: kapanmamış gün kuralı kapanış ANIYLA.
    idx = pd.to_datetime(["2026-09-30", "2026-10-01"])
    s = pd.Series([49.0, 49.03], index=idx)
    sina("14:30 UTC'de bugünün kapanışı yok", len(m.kapanmamis_bari_dusur(s, dt.datetime(2026, 10, 1, 14, 30, tzinfo=dt.timezone.utc))) == 1)
    sina("15:05 UTC'de bugünün kapanışı var", len(m.kapanmamis_bari_dusur(s, dt.datetime(2026, 10, 1, 15, 5, tzinfo=dt.timezone.utc))) == 2)
    src = (KOK / "ortak" / "usdtry.py").read_text(encoding="utf-8")
    sina("yükleyici saatlik kapanışı kuruyor", "_fx.saatlik_kapanislar(" in src and "_fx.gunluk_duzelt(" in src,
         "günlük barın kapanış alanı tek başına okunursa seri bir gün geriden gelir")
    # Satır SINIRIYLA sorulur: düz alt dize `ONCEKI_SUTUN = "usdtry_ist18"`
    # satırında da tutar ve sürüm geri alınsa bile geçerdi (03.10.2026'da tam
    # böyle yeşil geçti). Davranış aşağıdaki maddelerde ayrıca sorulur.
    sina("önbellek sütunu tanımı taşıyor (03.10.2026: cuma kuralıyla _2)",
         re.search(r'^SUTUN = "usdtry_ist18_2"$', src, re.M) is not None and "eski_tanim == SUTUN" in src
         and m.SUTUN != m.ONCEKI_SUTUN,
         "eski tanımlı önbellek taze sayılırsa yeni tanım hiç devreye girmez")
    # DAVRANIŞ: eski tanımla (günlük barın kapanış alanı) yazılmış ama TAZE bir
    # önbellek, tazelik kuralından geçse bile kullanılmaz; seri yeniden kurulur
    # ve önbellek yeni sütun adıyla yazılır. Kaynak metnini sormak yetmez: bir
    # koşul başka bir satırda geçebilir, davranış onu ayırır.
    import os
    simdi_ = dt.datetime(2026, 10, 2, 6, 26, tzinfo=dt.timezone.utc)
    gunler = pd.bdate_range("2026-06-01", "2026-10-01")
    with tempfile.TemporaryDirectory() as d_:
        yol = Path(d_) / "usdtry.csv"
        pd.Series(49.0, index=gunler, name="usdtry").to_csv(yol, index_label="tarih")   # eski sütun, taze mtime
        cekildi = []

        def cek(bas, bit):
            cekildi.append((bas, bit))
            return pd.Series(49.03, index=gunler)
        yedek = {v: os.environ.pop(v, None) for v in ("TTO_YENILE", "TTO_KOSU_BASLANGIC")}
        try:
            kr = m.seri(bas="2026-06-01", onbellek=yol, cek=cek, simdi=simdi_)
        finally:
            for v, x in yedek.items():
                if x is not None:
                    os.environ[v] = x
        sutun = pd.read_csv(yol, index_col=0).columns[0]
        sina("eski tanımlı taze önbellek kullanılmıyor, seri yeniden kuruluyor",
             cekildi and not kr.onbellekten and sutun == m.SUTUN, f"çekildi {len(cekildi)} · önbellekten "
             f"{kr.onbellekten} · sütun {sutun!r}")
        # Yeni tanımla yazılmış taze önbellek ise kullanılır (ağa çıkılmaz).
        cekildi.clear()
        kr2 = m.seri(bas="2026-06-01", onbellek=yol, cek=cek, simdi=simdi_)
        sina("yeni tanımlı taze önbellek kullanılıyor", not cekildi and kr2.onbellekten,
             f"çekildi {len(cekildi)} · önbellekten {kr2.onbellekten}")
        # Önbellekten dönen koşu künyesini taşır (tanım ve uyarı).
        m._kunye_yaz(yol, {"gecis": None, "kapanis": "İstanbul 18:00", "uyarilar": ["örnek uyarı"]})
        kr3 = m.seri(bas="2026-06-01", onbellek=yol, cek=cek, simdi=simdi_)
        sina("önbellekten dönen koşu künyenin uyarısını ve tanımını taşıyor",
             kr3.onbellekten and kr3.uyarilar == ["örnek uyarı"] and kr3.kapanis == "İstanbul 18:00", f"{kr3.uyarilar}")
        # YEDEK YOL: saatlik bar alınamadı, günlük bardan kurulan seri bir gün
        # geride. Eldeki İstanbul 18:00 serisi en az onun kadar yeniyse o döner
        # (hattın saati geri gitmez, gerileme kapısı ötmez) ve önbellek yedekle
        # EZİLMEZ.
        os.utime(yol, (0, 0))                                   # önbellek bayat: çekim denenir
        oncesi = yol.read_bytes()

        def cek_yedek(bas, bit):
            x = pd.Series(48.99, index=gunler[:-1])
            x.attrs = {"yedek": True, "uyari": "saatlik bar alınamadı (deneme); kapanış düzeltilmiş günlük bardan",
                       "kapanis": "Londra gece yarısı (günlük bar)"}
            return x
        kr4 = m.seri(bas="2026-06-01", onbellek=yol, cek=cek_yedek, simdi=simdi_)
        sina("yedek yol: eldeki yeni tanımlı seri döner, önbellek ezilmez",
             kr4.onbellekten and kr4.son == gunler[-1].date() and kr4.kapanis == "İstanbul 18:00"
             and any("saatlik bar alınamadı" in u for u in kr4.uyarilar) and yol.read_bytes() == oncesi,
             f"son {kr4.son} · {kr4.uyarilar}")
        # Önbellek yoksa yedek seri döner ama YENİ tanımın sütununa yazılmaz:
        # bir sonraki koşu onu taze bir İstanbul 18:00 serisi saymamalı.
        yol2 = Path(d_) / "usdtry2.csv"
        kr5 = m.seri(bas="2026-06-01", onbellek=yol2, cek=cek_yedek, simdi=simdi_)
        sutun5 = pd.read_csv(yol2, index_col=0).columns[0]
        cekildi.clear()
        kr6 = m.seri(bas="2026-06-01", onbellek=yol2, cek=cek, simdi=simdi_)
        sina("yedek seri yeni tanımın sütununa yazılmaz, bir sonraki koşu yeniden çeker",
             not kr5.onbellekten and kr5.kapanis.startswith("Londra") and sutun5 == m.YEDEK_SUTUN
             and cekildi and not kr6.onbellekten, f"sütun {sutun5!r} · çekildi {len(cekildi)}")
        # GEÇİŞ GÜNÜ: önbellek eski sütun adıyla duruyor (birleştirmeden sonraki
        # ilk koşu) ve saatlik bar alınamadı. Eldeki seri yedekten geride
        # değilse o döner — tanım şartı konsaydı yedek yayımlanır, hattın
        # saati bir gün geri gider ve gerileme kapısı hattı durdururdu.
        yol3 = Path(d_) / "usdtry3.csv"
        pd.Series(49.0, index=gunler, name="usdtry").to_csv(yol3, index_label="tarih")
        os.utime(yol3, (0, 0))
        oncesi3 = yol3.read_bytes()
        kr7 = m.seri(bas="2026-06-01", onbellek=yol3, cek=cek_yedek, simdi=simdi_)
        sina("geçiş günü yedek yol: eski sütunlu seri döner, saat geri gitmez, önbellek ezilmez",
             kr7.onbellekten and kr7.son == gunler[-1].date() and kr7.kapanis == m.ESKI_KAPANIS
             and yol3.read_bytes() == oncesi3, f"son {kr7.son} · {kr7.kapanis} · {kr7.uyarilar}")
        # Okura giden etiket kendi yapım tarihçemizi anlatmaz ("eski tanım"),
        # serinin sözleşmesini söyler; üç tanımın üç ayrı cevabı var.
        def agsiz_(bas, bit):
            raise RuntimeError("ağ yok (duman)")
        kr8 = m.seri(bas="2026-06-01", onbellek=yol3, cek=agsiz_, simdi=simdi_)
        yol4 = Path(d_) / "usdtry4.csv"
        m.seri(bas="2026-06-01", onbellek=yol4, cek=cek_yedek, simdi=simdi_)        # yedek sütunla yazar
        kr9 = m.seri(bas="2026-06-01", onbellek=yol4, cek=agsiz_, simdi=simdi_)
        metin = " ".join([kr7.kapanis, kr8.kapanis, kr9.kapanis] + kr7.uyarilar + kr8.uyarilar + kr9.uyarilar)
        sina("ağ düşünce etiket önbelleğin tanımını söyler (yedek → Londra gece yarısı, eski → günün başı)",
             kr9.kapanis.startswith("Londra") and kr8.kapanis == m.ESKI_KAPANIS
             and "eski tanım" not in metin.lower() and "ESKİ" not in metin, metin)
        # ÖLÇÜLEMEYEN GÜN: yalnız SAĞ UÇ uyarıdır. Tarihçenin ortasındaki
        # ölçülemeyen gün (yılbaşı) seriden düşer ama her koşuda okura basılan
        # bir uyarı değildir; son günden SONRAKİ ölçülemeyen gün ise kesintidir.
        orta = pd.Timestamp("2026-07-15")
        def cek_olc(sag):
            def _c(bas, bit):
                x = pd.Series(49.03, index=gunler[gunler != orta])
                x.attrs = {"kapanis": "İstanbul 18:00",
                           "olculemeyen": ["2026-07-15"] + (["2026-10-02"] if sag else [])}
                return x
            return _c
        k_orta = m.seri(bas="2026-06-01", onbellek=Path(d_) / "o1.csv", cek=cek_olc(False), simdi=simdi_)
        k_sag = m.seri(bas="2026-06-01", onbellek=Path(d_) / "o2.csv", cek=cek_olc(True), simdi=simdi_)
        sina("tarihçenin ortasındaki ölçülemeyen gün uyarı üretmez",
             not any("yetişmeyen" in u for u in k_orta.uyarilar) and orta not in k_orta.seri.index, f"{k_orta.uyarilar}")
        sina("son günden sonraki ölçülemeyen gün uyarıdır (yalnız o gün)",
             any("yetişmeyen" in u and "02.10.2026" in u and "15.07.2026" not in u for u in k_sag.uyarilar),
             f"{k_sag.uyarilar}")


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
                  ("Kapanış anı (İstanbul 18:00)", _kapanis_ani),
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
