#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten katmanlarının duman sınaması — ağsız, saniyeler içinde.

Neden var: bu depoyu birden çok oturum aynı gün düzenliyor ve aralarındaki
SÖZLEŞME KAYMASI kimsenin sınamadığı yerden vuruyor. 26.08.2026'da tam bu
oldu — bir oturum `_yayimlar()`'ı tek listeden (kayıtlar, alındı_mı) çiftine
çevirdi, başka bir oturum aynı gün onu tek liste sanan yeni bir çağrı ekledi.
Merge ikisini de sorunsuz aldı, iki değişiklik de kendi başına doğruydu, ama
birleşimleri üretimde TypeError verdi ve veri hattı düştü.

Bu dosya o sınıfın tamamını yakalar: her katmanın giriş noktasını GERÇEK depo
verisiyle çağırır. Ağ istemez, EVDS anahtarı istemez, saniyeler sürer — yani
her iş akışının en başında, ağa çıkmadan önce koşabilir.

Bir TANI aracı DEĞİLDİR: üretim kod yollarını sınar, düşerse iş akışı durmalı.
(Karşıtı için bkz. veri.yml'deki tazeleme raporu — o rapordur, durdurmaz.)
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import traceback
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
BULTENLER = BURASI.parent / "site" / "src" / "data" / "bulten"

gecen: list[str] = []
dusen: list[tuple[str, str]] = []


def sina(ad: str, fn):
    try:
        fn()
        gecen.append(ad)
    except Exception:                                          # noqa: BLE001
        dusen.append((ad, traceback.format_exc(limit=3).strip().splitlines()[-1]))


def son_bulten() -> dict | None:
    dosyalar = sorted(BULTENLER.glob("*.json")) if BULTENLER.exists() else []
    return json.loads(dosyalar[-1].read_text(encoding="utf-8")) if dosyalar else None


def _bicim():
    import sys as _s
    _s.path.insert(0, str(Path(__file__).resolve().parents[1] / "ortak"))
    import bicim as bc
    import olay as ol
    import rejim as rj
    assert bc.sayi(-1.247, 3) == "−1,247" and bc.sayi(1234.5) == "1.234,5"
    assert bc.yuzde(-1.884, 2) == "−%1,88" and bc.yuzde(0.4, 1, True) == "+%0,4"
    assert bc.degisim(-6.5, "bp", 1) == "−6,5 bp" and bc.degisim(0.4, "%") == "+%0,40"
    assert bc.sayi(-0.001, 2) == "0,00", "yuvarlanan sıfır işaret taşımaz"
    assert ol._s(-696.0, 0) == "−696" and ol._s(0.4, 1, True) == "+0,4"
    assert rj.redk_konum(7.3) == "on yıllık ortalamanın %7,3 üstünde", rj.redk_konum(7.3)
    assert rj.redk_konum(-3.2) == "on yıllık ortalamanın %3,2 altında", rj.redk_konum(-3.2)
    assert rj.redk_konum(None) == ""
    import denetim as dn
    class _D(dn.Denetim):
        def __init__(self, b):
            self.b = b; self.gecen = []; self.uyari = []; self.engel = []; self.ayrinti = False
    d = _D({"tarih": "2026-09-01", "yorum": {"giris": "<p>Endeks -1.247'den -696'ya geçti; sapma %+7.3 oldu.</p>"}})
    d.bicim()
    assert any("ASCII eksi" in u for u in d.uyari), d.uyari
    assert any("ondalık noktası" in u for u in d.uyari), d.uyari
    d2 = _D({"tarih": "2026-09-01", "yorum": {"giris": "<p>Endeks −1,247'den −696'ya geçti; %7,3 üstünde. Veri 31.08.2026.</p>"}})
    d2.bicim()
    assert not d2.uyari, d2.uyari


def main() -> int:
    import ayar, denetim, gozlem, grafik_veri, olay, rejim, soz, surpriz, tazeleme, uret

    hat = next(iter(ayar.RITIM))
    bugun = dt.date.today()

    # ── anlık görüntü deposu: anahtar başına saat sözleşmesi
    def _gozlem():
        d = gozlem.anlik(hat) or {}
        gozlem.anahtar_tarihi(d, "yok_boyle_bir_anahtar")
        gozlem.onceki_surum_anahtar(hat, "yok_boyle_bir_anahtar", "", "")
        gozlem.son_gorulme(hat)
        gozlem.alan_son_gorulme(hat, "_tarih")
        gozlem.anahtar_hafta_once(hat, "_tarih")
    sina("gozlem: saat yardımcıları", _gozlem)

    # ── olay motoru ve yeni katmanlar
    sina("olay.topla", lambda: olay.topla())
    sina("olay.gecikme_olaylari", lambda: olay.gecikme_olaylari())
    sina("rejim.panosu", lambda: rejim.panosu())
    sina("soz.ozet", lambda: soz.ozet(bugun.isoformat()))
    sina("grafik_veri.hazirla", lambda: grafik_veri.hazirla())
    sina("surpriz.gecmis_olaylar", lambda: surpriz.gecmis_olaylar([], {}, bugun))
    sina("uret.gostergeler (günlük)", lambda: uret.gostergeler(haftalik=False))
    sina("uret.gostergeler (haftalık)", lambda: uret.gostergeler(haftalik=True))

    # ── tazeleme: takvim ucu SAHTE, sözleşme gerçek
    def _tazeleme():
        gercek = tazeleme._yayimlar
        sahte = [{"adi": "TCMB Analitik Bilanço", "kurum": "TCMB",
                  "an": "2026-01-02T14:30:00"}]
        try:
            for kayitlar, alindi in ((sahte, True), ([], False)):
                tazeleme._yayimlar = lambda y, k=kayitlar, a=alindi: (k, a)
                tazeleme.kararlar(simdi=dt.datetime(2026, 1, 3, 16, 0))
                tazeleme.olu_kaliplar()
                tazeleme.gerekli(simdi=dt.datetime(2026, 1, 3, 16, 0))
        finally:
            tazeleme._yayimlar = gercek
    sina("tazeleme: karar + ölü kalıp (iki takvim durumu)", _tazeleme)

    # ── ortak HTTP emniyeti: zaman aşımı gerçekten takılıyor mu (ağsız)
    # 2026-08-27: tcmb istemcisi isteği timeout'suz atıyordu; EVDS 21 dakika
    # astı ve dört hattın üçünün tamamlanmış işi çöpe gitti. Emniyet artık
    # ortak/sitecustomize.py'de; SINANMAYAN emniyet emniyet değildir.
    def _http_emniyet():
        import importlib.util
        import requests
        yol = BURASI.parent / "ortak" / "sitecustomize.py"
        assert yol.exists(), f"{yol} yok"
        asil = requests.sessions.Session.request
        onceden = getattr(requests.sessions.Session, "_tto_emniyet", False)
        gorulen: dict = {}

        class _Yanit:                      # ağa hiç çıkılmaz
            status_code = 200

        def _kaydet(self, method, url, **kw):
            gorulen["timeout"] = kw.get("timeout")
            return _Yanit()

        try:
            requests.sessions.Session.request = _kaydet
            if onceden:                    # zaten sarılıysa yeniden sarılsın
                del requests.sessions.Session._tto_emniyet
            spec = importlib.util.spec_from_file_location("_tto_emniyet_sinama", yol)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            assert getattr(requests.sessions.Session, "_tto_emniyet", False), \
                "emniyet kurulmadı"
            requests.get("http://sinama.gecersiz/x")
            zaman = gorulen.get("timeout")
            assert isinstance(zaman, tuple) and all(zaman), \
                f"varsayılan zaman aşımı takılmadı: {zaman!r}"
            requests.get("http://sinama.gecersiz/y", timeout=7)
            assert gorulen.get("timeout") == 7, \
                f"açıkça verilen zaman aşımı ezildi: {gorulen.get('timeout')!r}"
        finally:
            requests.sessions.Session.request = asil
            if onceden:
                requests.sessions.Session._tto_emniyet = True
            else:
                try:
                    del requests.sessions.Session._tto_emniyet
                except AttributeError:
                    pass
    sina("ortak: HTTP zaman aşımı emniyeti", _http_emniyet)

    # ── denetim: son bülten üzerinde bütün ölçütler
    b = son_bulten()
    if b is None:
        dusen.append(("denetim", "sınanacak bülten dosyası yok"))
    else:
        def _denetim():
            d = denetim.Denetim(b)
            for olcut in ("yazi", "veri", "atif", "sayi", "nabiz",
                          "tema", "izleme", "dil", "tazelik", "karanlik"):
                getattr(d, olcut)()
        sina("denetim: on ölçüt", _denetim)

    # ── zincir raporu: yazı katmanının sabah attığı ilk adım
    def _zincir():
        import contextlib, io as _io
        import zincir
        with contextlib.redirect_stdout(_io.StringIO()):
            kod, _ = zincir.durum()
        assert kod in (0, 1, 2, 3, 4), f"beklenmeyen zincir kodu: {kod}"
    sina("zincir: durum raporu", _zincir)

    # ── YAZILMIŞ BÜLTEN KORUNUYOR MU (27.08.2026 kusuru)
    #
    # uret.yaz() yorumu ve gündemi koruyordu ama ÖZETİ korumuyordu: ozet_ekle()
    # her koşuda b["ozet"]'i makine özetiyle eziyor, yazı katmanının "ne oldu /
    # ne bekleniyor" paragrafları sessizce kayboluyordu. Sayfa yine "yazılı"
    # göründüğü için de hiçbir denetim itiraz etmiyordu. Kusur geri konarak
    # sınandı: koruma kaldırılınca bu sınama düşüyor.
    def _koruma():
        import tempfile
        import uret as _uret
        eski_cikti = _uret.CIKTI
        try:
            _uret.CIKTI = Path(tempfile.mkdtemp())
            yazili = {
                "tarih": "2026-01-02", "gundem_kaynagi": "yazili",
                "yorum": "<p>yazı katmanının yorumu</p>", "yorum_zamani": "2026-01-02",
                "gundem": {"kilit": "<p>yazılı gündem</p>"},
                "ozet": {"ne_oldu": "<p>yazılı özet</p>", "ne_bekleniyor": "<p>ileriye</p>"},
            }
            (_uret.CIKTI / "2026-01-02.json").write_text(
                json.dumps(yazili, ensure_ascii=False), encoding="utf-8")
            # Deterministik koşunun ürettiği taban: üçü de makine metni.
            taban = {"tarih": "2026-01-02", "gundem_kaynagi": "otomatik",
                     "yorum": "", "gundem": {"kilit": "<p>taban</p>"},
                     "ozet": {"ne_oldu": "<p>makine özeti</p>", "ne_bekleniyor": ""}}
            _uret.yaz(taban)
            son = json.loads((_uret.CIKTI / "2026-01-02.json").read_text(encoding="utf-8"))
            assert son["yorum"] == yazili["yorum"], "yorum ezildi"
            assert son["gundem"] == yazili["gundem"], "gündem ezildi"
            assert son["ozet"] == yazili["ozet"], "ÖZET EZİLDİ"
            assert son["gundem_kaynagi"] == "yazili", "yayın kapısı düştü"
        finally:
            _uret.CIKTI = eski_cikti
    sina("uret.yaz: yazılmış bülten korunuyor", _koruma)

    # YERLEŞMEMİŞ BAR. 27.08 bülteni 04:21 UTC'de koştu ve 51 enstrümanın 21'i
    # o anda HENÜZ AÇIK olan günün barını taşıyordu; kapanışa göre değişimleri
    # "günlük değişim" diye yayımlandı. Altında bu, işareti ters çevirdi:
    # dünkü seans −%0,86 kapanmışken bülten "+%1,78" yazdı ve günün anlatısını
    # o sahte hareketin üzerine kurdu. Koruma vardı ama yalnız beş enerji
    # vadelisini kapsıyordu. Bu sınama korumayı SAHTE SAATLE çağırır: kusur
    # geri konarsa (eşik tablosundan bir grup düşerse) burada düşer.
    def _yerlesmemis():
        from datetime import datetime as _dt, timezone as _tz
        import piyasa as _piyasa

        bugun, dun = "2026-08-27", "2026-08-26"
        ornek = {
            "GC=F": "metal", "EURUSD=X": "g10_fx", "BTC-USD": "kripto",
            "^N225": "asya_hisse", "XU100.IS": "tr_hisse",
        }
        gercek = _piyasa.datetime
        try:
            class _Saat(_dt):
                @classmethod
                def now(cls, tz=None):
                    return _dt(2026, 8, 27, 4, 21, tzinfo=_tz.utc)
            _piyasa.datetime = _Saat
            seri = {k: {"tarih": [dun, bugun], "kapanis": [100.0, 110.0]} for k in ornek}
            _piyasa._yerlesmemis_dus(seri)
            for k in ornek:
                assert seri[k].get("yerlesmemis_dusuruldu"), f"{k}: bugünün barı düşmedi"
                assert seri[k]["tarih"][-1] == dun, f"{k}: seri {dun}'da bitmeli"

            # Kapanmış piyasa: aynı bar 22:00 UTC'de KULLANILMALI, yoksa
            # koruma bir günlük gecikmeyi kalıcı hâle getirir.
            class _Gec(_dt):
                @classmethod
                def now(cls, tz=None):
                    return _dt(2026, 8, 27, 22, 30, tzinfo=_tz.utc)
            _piyasa.datetime = _Gec
            gec = {"GC=F": {"tarih": [dun, bugun], "kapanis": [100.0, 110.0]}}
            _piyasa._yerlesmemis_dus(gec)
            assert not gec["GC=F"].get("yerlesmemis_dusuruldu"), "kapanmış bar boşuna düştü"

            # Tanımsız grup: bilinmeyen bir kod bugünün barına GÜVENMEMELİ.
            _piyasa.datetime = _Saat
            bilinmeyen = {"YOK=F": {"tarih": [dun, bugun], "kapanis": [100.0, 110.0]}}
            _piyasa._yerlesmemis_dus(bilinmeyen)
            assert bilinmeyen["YOK=F"].get("yerlesmemis_dusuruldu"), "tanımsız grup düşmedi"
        finally:
            _piyasa.datetime = gercek
    sina("piyasa: yerleşmemiş bar düşürülüyor", _yerlesmemis)

    # DENETİMİN SON KAPISI. Ölçüm katmanındaki koruma tek başına yetmiyor: bir
    # zamanlar yalnız beş enerji vadelisini kapsıyordu ve kimse fark etmedi.
    # denetim.yerlesmemis aynı soruyu yayının son kapısında bağımsız sorar; bu
    # sınama onun GERÇEKTEN engel ürettiğini doğrular.
    def _denetim_yerlesmemis():
        from datetime import datetime as _dt, timezone as _tz
        import denetim as _den
        gercek = _den.datetime
        try:
            class _Saat(_dt):
                @classmethod
                def now(cls, tz=None):
                    return _dt(2026, 8, 27, 4, 21, tzinfo=_tz.utc)
            _den.datetime = _Saat
            b = {"tarih": "2026-08-27", "piyasa": {"gruplar": [
                {"id": "metal", "satirlar": [{"ad": "Altın", "tarih": "2026-08-27", "d1": 1.78}]},
                {"id": "asya_hisse", "satirlar": [{"ad": "Nikkei", "tarih": "2026-08-26", "d1": 0.3}]},
            ]}}
            d = _den.Denetim(b); d.yerlesmemis()
            assert d.engel and "KAPANMAMIŞ" in d.engel[0], "kapanmamış bar engel üretmedi"

            temiz = {"tarih": "2026-08-27", "piyasa": {"gruplar": [
                {"id": "metal", "satirlar": [{"ad": "Altın", "tarih": "2026-08-26", "d1": -0.86}]},
            ]}}
            d2 = _den.Denetim(temiz); d2.yerlesmemis()
            assert not d2.engel, "kapanmış bar boşuna engellendi"
        finally:
            _den.datetime = gercek
    sina("denetim: kapanmamış bar ENGEL", _denetim_yerlesmemis)

    # SEANS ETİKETİ. 31.08.2026 pazartesi bülteninde elli piyasa satırının
    # ellisi 28.08 Cuma kapanışını taşıyordu ve "günlük değişim" diye
    # yayımlandı — hangi seansa ait olduğunu söyleyen hiçbir alan yoktu.
    # Ölçüt üç durumu ayırmalı: pazartesi/Cuma NORMAL, tek tatil UYARI,
    # ikiden fazla kaçırılan seans ENGEL. Takvim günüyle ölçmek tek tatili
    # bile engel sayardı; sınama tam bu ayrımı zorluyor.
    def _denetim_piyasa_seansi():
        import denetim as _den
        def calistir(bulten, kapanis, etiket=True):
            d = _den.Denetim({"tarih": bulten, "piyasa": {
                "kapanis_tarih": kapanis,
                "kapanis_seansi": f"{kapanis} kapanışı" if etiket else None}})
            d.piyasa_seansi()
            return d
        d = calistir("2026-08-31", "2026-08-28")          # Pzt bülteni, Cuma kapanışı
        assert not d.engel and not d.uyari, f"normal hafta sonu boşluğu şikâyet üretti: {d.engel + d.uyari}"
        d = calistir("2026-09-01", "2026-08-28")          # bir tatil kaçırılmış
        assert d.uyari and not d.engel, "tek kaçırılan seans uyarı üretmedi ya da engel oldu"
        d = calistir("2026-09-02", "2026-08-28")          # iki seans kaçırılmış
        assert d.engel and "BAYAT" in d.engel[0], "iki kaçırılan seans ENGEL üretmedi"
        d = calistir("2026-08-31", "2026-08-28", etiket=False)
        assert d.uyari and "ETİKET" in d.uyari[0], "seans etiketi eksikken uyarı çıkmadı"
        d = calistir("2026-08-31", None)
        assert d.uyari, "seans tarihi hiç yokken uyarı çıkmadı"

    sina("denetim: piyasa seansı etiketli ve bayat değil", _denetim_piyasa_seansi)

    # HAFTA SONU BOŞLUĞU σ'YI ŞİŞİRMİYOR — ölçülen olgu koda bağlanıyor.
    # Sezgi "pazartesi hareketi üç takvim günü kapsar, günlük σ ile kıyaslamak
    # onu olağandışı gösterir" der. Ölçüm bunun tersini söyledi (σ3/σ1 medyanı
    # 1,00). Bu sınama, birinin ileride d1_sigma'ya boşluk ölçeklemesi
    # eklemesini yakalar: aynı hareket, farklı boşlukla, aynı σ'yı vermelidir.
    def _sigma_boslugu_olceklemez():
        import piyasa as _p
        k = [100.0 + i * 0.1 for i in range(25)]
        t_bitisik = [f"2026-01-{i + 1:02d}" for i in range(25)]      # ardışık günler
        t_bosluklu = list(t_bitisik[:-1]) + ["2026-01-27"]           # son adım 3 gün sonra
        a = _p.satir(_p.VARLIKLAR[0], {_p.VARLIKLAR[0].kod: {"kapanis": k, "tarih": t_bitisik}})
        b = _p.satir(_p.VARLIKLAR[0], {_p.VARLIKLAR[0].kod: {"kapanis": k, "tarih": t_bosluklu}})
        assert a["d1_sigma"] == b["d1_sigma"], (
            "boşluk σ'yı değiştirdi — kapanıştan kapanışa hareket tek seanslık "
            "risktir, ölçekleme uygulanmamalı")
        assert a["gap_gun"] == 1 and b["gap_gun"] == 3, "gap_gun takvim boşluğunu vermiyor"

    sina("piyasa: σ takvim boşluğuna göre ölçeklenmiyor", _sigma_boslugu_olceklemez)

    # HAFTALIK BÜLTENİN PENCERESİ HAFTADIR. 30.08.2026'ya kadar haftaya bakış
    # bülteni günlük σ listesini basıyor ve sayfada "Günün olağandışı
    # hareketleri" başlığı duruyordu. Kusur geri konarak sınanıyor: haftalık
    # bültene günlük kipli bir liste verilirse denetim ENGEL üretmeli.
    def _denetim_sigma_penceresi():
        import denetim as _den
        liste = [{"ad": "USD/CHF", "deger": 1.21, "birim": "%", "sigma": 1.4, "oynaklik": 0.85}]
        yanlis = {"tarih": "2026-08-30", "haftalik": True,
                  "piyasa": {"en_cok_hareket": {"sigma": liste, "sigma_kip": "gunluk"}}}
        d = _den.Denetim(yanlis); d.olagandisilik_penceresi()
        assert d.engel and "PENCERESİ YANLIŞ" in d.engel[0], \
            "haftalık bültende günlük σ listesi engel üretmedi"

        # Kip hiç bildirilmemişse (eski ölçüm kodu) sessiz geçilmemeli.
        eksik = {"tarih": "2026-08-30", "haftalik": True,
                 "piyasa": {"en_cok_hareket": {"sigma": liste}}}
        d2 = _den.Denetim(eksik); d2.olagandisilik_penceresi()
        assert d2.engel and "BİLDİRİLMEMİŞ" in d2.engel[0], "kip eksikken engel çıkmadı"

        # Doğru kip boşuna engellenmemeli — ne haftalıkta ne günlükte.
        for hafta, kip in ((True, "haftalik"), (False, "gunluk")):
            ok = {"tarih": "2026-08-30", "haftalik": hafta,
                  "piyasa": {"en_cok_hareket": {"sigma": liste, "sigma_kip": kip}}}
            d3 = _den.Denetim(ok); d3.olagandisilik_penceresi()
            assert not d3.engel, f"doğru kip ({kip}) boşuna engellendi"
    sina("denetim: olağandışılık penceresi bültenin kipini izliyor", _denetim_sigma_penceresi)

    # SAYFADAKİ TEMA METNİ DEFTERDEKİNDEN ESKİ OLABİLİR. Tema bölümü bültene
    # ÖLÇÜM anında işleniyor, yazı katmanı defteri ondan SONRA güncelliyor;
    # yani defteri düzeltmek sayfayı düzeltmiyor. İki kez yayına çıktı (28.08
    # geri alınmış rakamlar, 30.08 "konuşma bugün" derken konuşma iki gün
    # önce yapılmıştı). Ölçüt farkı ölçüyor; bu sınama farkı geri koyuyor.
    def _denetim_tema_goruntusu():
        import denetim as _den
        defter = json.loads((BURASI / "temalar.json").read_text(encoding="utf-8"))
        canli = [x for x in (defter.get("temalar") or [])
                 if x.get("durum") in ("aktif", "izlemede")]
        assert canli, "defterde canlı tema yok — sınama kurulamıyor"

        taze = {"tarih": "2026-08-30", "temalar": {"temalar": defter["temalar"]}}
        d = _den.Denetim(taze); d.tema()
        assert not [e for e in d.engel if "TEMA GÖRÜNTÜSÜ ESKİ" in e], \
            "defterle birebir aynı görüntü boşuna engellendi"

        eski = json.loads(json.dumps(defter["temalar"]))
        for x in eski:
            if x.get("durum") in ("aktif", "izlemede"):
                x["gelisme"] = "<p>Çürütücü ölçüt bugün sınanacak.</p>"
                break
        bayat = {"tarih": "2026-08-30", "temalar": {"temalar": eski}}
        d2 = _den.Denetim(bayat); d2.tema()
        assert [e for e in d2.engel if "TEMA GÖRÜNTÜSÜ ESKİ" in e], \
            "sayfadaki eski tema metni engel üretmedi"
    sina("denetim: eski tema görüntüsü ENGEL", _denetim_tema_goruntusu)

    # HAFTALIK σ'NIN KENDİSİ. Pencereler ÖRTÜŞMEMELİ: örtüşen haftalık
    # pencereler ardışık bağımlılık taşır, standart sapmayı küçültür ve her
    # hareketi olağandışı gösterir. Ayrıca haftalık σ günlüğün ~√5 katı
    # mertebesinde çıkmalı; çıkmıyorsa birim ya da pencere karışmıştır.
    def _haftalik_sigma():
        import piyasa as _piyasa
        kapanis = [100.0 * (1.01 ** i) for i in range(120)]      # düzgün artan seri
        d = _piyasa._haftalik_degisimler(kapanis, False, 20)
        assert len(d) == 20, f"20 haftalık gözlem beklenirken {len(d)} geldi"
        bek = (1.01 ** 5 - 1) * 100
        assert all(abs(x - bek) < 1e-6 for x in d), "haftalık değişim beşer günlük değil"

        import random
        random.seed(7)
        yol, v = [100.0], 100.0
        for _ in range(400):
            v *= 1 + random.gauss(0, 0.01)
            yol.append(v)
        sg = _piyasa._oynaklik(yol, False)
        sh = _piyasa._oynaklik_hafta(yol, False)
        assert sg and sh, "σ hesaplanamadı"
        oran = sh / sg
        assert 1.4 < oran < 3.4, (
            f"haftalık σ günlüğün {oran:.2f} katı — √5≈2,24 mertebesinde olmalı; "
            "pencere ya da birim karışmış olabilir")

        # Tarihçe yetmiyorsa σ ÜRETİLMEZ; yarım veriyle sıralama kurulmaz.
        assert _piyasa._oynaklik_hafta([100.0] * 20, False) is None, \
            "kısa tarihçede haftalık σ üretildi"
    sina("piyasa: haftalık σ örtüşmeyen pencerelerle kuruluyor", _haftalik_sigma)

    # SAYFA ETİKETLERİ DE PENCEREYİ İZLEMELİ. Ölçüm katmanını haftalığa çevirmek
    # yetmiyor: σ bloğu üç ayrı yerde basılıyor (bülten gövdesi, çubuk grafik,
    # ana sayfa) ve üçünde de başlık/oynaklık etiketi SABİT "günlük" yazıyordu.
    # 30.08.2026'da ölçü haftalığa geçtiğinde ana sayfa haftalık oynaklıkları
    # "20g oynaklık" diye etiketledi — sayı doğru, etiket yalan. Bu sınama
    # etiketin türetildiğini yapısal olarak dayatır: dosyalar kipe bakmıyorsa
    # düşer. (Astro'yu Python'dan koşturamayız; ölçebileceğimiz şey bağın
    # kurulu olduğu.)
    def _sayfa_kipi():
        kok = BURASI.parent / "site" / "src"
        beklenen = {
            "components/SigmaSerit.astro": ("kip", "pencereAd"),
            "components/BultenGovde.astro": ("sigma_kip", "sigmaBaslik"),
            "pages/index.astro": ("sigmaKip", "sigmaBaslik", "oynaklikEtiketi"),
            "lib/anaSayfa.ts": ("sigmaKip", "sigma_kip"),
        }
        for yol, anahtarlar in beklenen.items():
            f = kok / yol
            assert f.exists(), f"{yol} bulunamadı — σ etiketi sınanamıyor"
            metin = f.read_text(encoding="utf-8")
            for a in anahtarlar:
                assert a in metin, (
                    f"{yol} içinde '{a}' yok — σ başlığı/etiketi bültenin kipinden "
                    "türetilmiyor olabilir, sabit 'günlük' yazan sürüme dönülmüş")
        govde = (kok / "components/BultenGovde.astro").read_text(encoding="utf-8")
        assert "kip={b.piyasa.en_cok_hareket.sigma_kip}" in govde, \
            "SigmaSerit'e kip geçirilmiyor — grafik başlığı sabit 'günlük' kalır"
        ana = (kok / "pages/index.astro").read_text(encoding="utf-8")
        assert "20g oynaklık {" not in ana and ">20g oynaklık<" not in ana, \
            "ana sayfada oynaklık etiketi yeniden sabitlenmiş"
    sina("sayfa: σ başlıkları bültenin kipinden türüyor", _sayfa_kipi)

    # Kilit gelişme ölçütü KAPANABİLİR olmalı. İngilizce başlığın kelimelerini
    # Türkçe metinde arayan eski hâli hiçbir zaman kapanmıyordu; kapanamayan
    # uyarı, yazarı bütün uyarıları görmezden gelmeye alıştırır.
    def _kilit_capa():
        import denetim as _den
        madde = {"baslik": "Gold Rises As Treasury Buyback Support Plan Weighs On Dollar",
                 "kaynak": "Arama — ABD borç yönetimi ve tahvil arzı (+8 kaynak)"}
        ozel, konu = _den._kilit_capalari(madde)
        assert konu, "Türkçe konu çapası çıkarılamadı"
        assert any(w in _den._sade("Hazine geri alımı ve tahvil arzı tartışması") for w in konu), \
            "Türkçe konu çapası metinde bulunamadı"
        bos = {"baslik": "Stocks up", "kaynak": ""}
        o2, k2 = _den._kilit_capalari(bos)
        assert not o2 and not k2, "çapasız maddeden çapa üretildi (uyarı kapanamaz olurdu)"
    sina("denetim: kilit gelişme çapası kapanabilir", _kilit_capa)

    # Devir düzeltmesi, KAPANMAMIŞ bar elindeyken koşarsa bugüne sahte bir devir
    # yazıyor ve o devirden önceki bütün günleri yanlış oranla ölçekliyordu.
    # Sıra artık bağlayıcı: önce bar düşer, sonra devir hesaplanır.
    def _sira():
        import piyasa as _piyasa
        metin = Path(_piyasa.__file__).read_text(encoding="utf-8")
        i_bar = metin.index("seri = _yerlesmemis_dus(seri)")
        i_roll = metin.index("seri = _roll_duzelt(seri)")
        assert i_bar < i_roll, ("SIRA TERS: devir düzeltmesi kapanmamış bar elindeyken "
                                "koşuyor — bugüne sahte devir yazar")
    sina("piyasa: bar düşürme devir düzeltmesinden ÖNCE", _sira)

    # SAKAT ÖLÇÜM YAZILMAZ. Rutin metni "dosya yoksa bulten.py ile üret" diyor;
    # o oturumda ağ kapalı ve deneme 0 enstrümanlık bir fotoğraf üretiyor.
    # Rutin metnini bir aracı düzeltemiyor (27.08'de denendi, reddedildi), o
    # yüzden kapı koda kondu. Bu sınama kapının GERÇEKTEN kapandığını doğrular.
    def _sakat():
        # bulten.py depo KÖKÜNDE, bulten/ paketinde değil — yol ile okunur.
        kaynak = (Path(__file__).resolve().parent.parent / "bulten.py").read_text(encoding="utf-8")
        assert "ASGARI_ENSTRUMAN" in kaynak, "sakat ölçüm kapısı yok"
        i_kapi = kaynak.index("n_enst < _denetim.ASGARI_ENSTRUMAN")
        i_yaz = kaynak.index("y = uret.yaz(b)")
        assert i_kapi < i_yaz, "kapı yazmadan SONRA geliyor — dosya yine de yazılır"
        assert "if not a.sakat_yaz:" in kaynak, "kapı geçersiz kılınabilir değil"
    sina("bulten.py: sakat ölçüm yazılmıyor", _sakat)

    # FX GÜNLÜK KİPİ GERÇEKTEN VERİ ÇEKMELİ. Hattın hafif kipi bir zamanlar
    # günlük listedeydi ve orada yaptığı tek iş sahte tazelik damgası atmaktı:
    # mevcut veriden grafik çiziyor, haber akışını HİÇ toplamıyordu (63fbf6e).
    # Günlük kip o hatayı tekrarlamamalı — adım listesinde veri çeken `run.py`
    # BULUNMAK ZORUNDA, ve ağır arşiv bayrağı BULUNMAMALI.
    def _fx_gunluk():
        # guncelle.py depo KÖKÜNDE; duman.py sys.path'e bulten/ ekliyor.
        kok = str(Path(__file__).resolve().parent.parent)
        if kok not in sys.path:
            sys.path.insert(0, kok)
        import guncelle as mod
        fx = next(h for h in mod.HATLAR if h.ad == "fx")

        g = fx.adimlar(tam=False, gunluk=True)
        assert any(a.split()[0] == "run.py" for a in g), \
            "günlük kip veri çekmiyor — sahte tazelik damgası geri geldi"
        assert not any("--fetch-history" in a for a in g), \
            "günlük kip ağır GDELT arşivini çekiyor"
        assert any(a.startswith("web_cikti.py") and "--anlik" in a for a in g), \
            "günlük kip haftalık panelleri de yeniden çiziyor"

        h = fx.adimlar(tam=False, gunluk=False)
        assert not any(a.split()[0] == "run.py" for a in h), \
            "hafif kip veri çeker hâle gelmiş — kipler karışmış"
        # Günlük kipi tanımsız bir hat sessizce hafife düşmeli.
        baska = next(x for x in mod.HATLAR if x.ad == "tcmb")
        assert baska.adimlar(False, True) == baska.adimlar(False), \
            "günlük kipi tanımsız hat hafife düşmüyor"

        # BAĞIMLILIK: günlük kip run.py koşturduğu için torch/transformers
        # KURULMAK zorunda. İlk günlük koşu (28.08) hafif paket listesiyle
        # açıldı ve 15 saniyede düştü — bu sınama o kusuru kilitler.
        hafif = mod._req_paketler(mod.KOK / fx.klasor, agir_dahil=False)
        assert "torch" not in hafif, "hafif liste ağır paket taşıyor"
        import inspect
        for fn in (mod.eksik_paketler, mod.sistem_kur):
            assert "gunluk" in inspect.signature(fn).parameters, \
                f"{fn.__name__} günlük kipi tanımıyor"
            assert "tam or gunluk" in inspect.getsource(fn), \
                f"{fn.__name__} günlük kipte ağır paketleri saymıyor"
    sina("guncelle: fx günlük kipi veri çekiyor", _fx_gunluk)

    # SÜRPRİZ GELİŞ KURALI. "Geldi" kararı eskiden yalnız referans tarihine
    # bakıyordu (veri_gun >= yayım günü) ve haftalık TCMB serilerinde bu
    # YAPISAL olarak imkânsızdı: 27.08 Perşembe yayımı 21.08 dönemini taşır.
    # 28.08 bülteni, gösterge panosu 14.08→21.08 İLERLEMİŞKEN aynı yayım için
    # "veri henüz hatta düşmedi" yazdı. Kural artık sürüm saatine de bakıyor;
    # bu sınama iki yönü de kilitler: sürüm yayımdan SONRA ilerlediyse geldi,
    # yayımdan ÖNCE kalmışsa gelmedi (erken ilan yasak).
    def _surpriz_gelis():
        import datetime as _dt
        import surpriz as _s
        import gozlem as _g

        g_anlik, g_son, g_onceki = _g.anlik, _g.son_gorulme, _g.onceki_surum_anahtar
        s_arsivle, s_oku = _s.arsivle, _s.arsiv_oku
        try:
            _g.anlik = lambda hat: {"g_ar_13y": 23.7, "_tarih": "21.08.2026"}
            _g.onceki_surum_anahtar = lambda *a, **k: {"d": {"g_ar_13y": 25.9}}
            _s.arsivle = lambda k: None
            _s.arsiv_oku = lambda: {"x": {
                "tarih": "2026-08-27", "olay": "TCMB: Haftalık para-banka (34. Hafta)",
                "beklenti": "", "beklenti_sayi": None}}

            # (a) referans (21.08) < yayım (27.08) AMA sürüm 28.08'de ilerledi → GELDİ
            _g.son_gorulme = lambda hat: ("21.08.2026", "2026-08-28T04:17:15")
            r = _s.gecmis_olaylar([], piyasa=None, bugun=_dt.date(2026, 8, 28))
            assert r and r[0]["durum"] == "geldi", f"sürüm ilerledi ama durum: {r[0]['durum'] if r else 'boş'}"
            assert r[0]["gerceklesme"] == 23.7 and r[0]["onceki"] == 25.9

            # (b) sürüm yayımdan ÖNCE (20.08) kalmış → GELMEDİ (erken ilan yasak)
            _g.son_gorulme = lambda hat: ("14.08.2026", "2026-08-20T13:09:00")
            _g.anlik = lambda hat: {"g_ar_13y": 25.9, "_tarih": "14.08.2026"}
            r = _s.gecmis_olaylar([], piyasa=None, bugun=_dt.date(2026, 8, 28))
            assert r and r[0]["durum"] == "veri henüz hatta düşmedi", \
                f"bayat sürüm 'geldi' sayıldı: {r[0]['durum'] if r else 'boş'}"
            assert r[0]["gerceklesme"] is None, "gelmemiş veri için gerçekleşme yazıldı"
        finally:
            _g.anlik, _g.son_gorulme, _g.onceki_surum_anahtar = g_anlik, g_son, g_onceki
            _s.arsivle, _s.arsiv_oku = s_arsivle, s_oku
    sina("surpriz: geliş sürüm saatinden okunuyor", _surpriz_gelis)

    # ── yaz.py: düzeltme kaydı biçimce sınanır; denetim yarım kaydı engeller
    def _duzeltme():
        import yaz
        b = {"gundem_kaynagi": "yazili", "gundem": {"kilit": "x"}}
        import tempfile, json as _j
        with tempfile.TemporaryDirectory() as td:
            hedef = Path(td) / "b.json"
            hedef.write_text(_j.dumps(b), encoding="utf-8")
            yeni, degisen = yaz.uygula(hedef, {"duzeltmeler": [
                {"alan": "Brent günlük değişim (28.08)", "eski": "−%11,36", "yeni": "−%1,74",
                 "sebep": "vadeli devir düzeltmesi kurulamamıştı"}]})
            assert yeni["duzeltmeler"][0]["tarih"], "tarih doldurulmadı"
            assert any("duzeltmeler" in d for d in degisen), degisen
            try:
                yaz.uygula(hedef, {"duzeltmeler": [{"alan": "x", "eski": "1"}]})
            except SystemExit as e:
                assert "yeni" in str(e), str(e)
            else:
                raise AssertionError("eksik alanlı düzeltme kabul edildi")
        d = denetim.Denetim({**b, "duzeltmeler": [{"alan": "x", "eski": "", "yeni": "2"}]})
        d.duzeltme()
        assert any("Düzeltme kaydı" in e for e in d.engel), d.engel
        d2 = denetim.Denetim({**b, "yorum": "<p>Yayımlanan −%11,36 yerine gerçek hareket −%1,74.</p>"})
        d2.duzeltme()
        assert any("duzeltmeler kaydı boş" in u for u in d2.uyari), d2.uyari
    sina("yaz/denetim: düzeltme kaydı biçimce tam, yarım kayıt engel", _duzeltme)

    # ── yaz.py: yazı katmanının TEK giriş kapısı — sözleşmesi sınanır
    def _yaz():
        import yaz, tempfile, json as _j, subprocess as _sp, os as _os, time as _t
        with tempfile.TemporaryDirectory() as td:
            hedef = Path(td) / "2026-01-05.json"
            b0 = {"tarih": "2026-01-05", "olusturma": "2026-01-05T04:00:00+00:00",
                  "gundem_kaynagi": "taban", "yorum": "<p>eski</p>", "gundem": {}}
            hedef.write_text(_j.dumps(b0), encoding="utf-8")
            # (a) yabancı alan reddi
            try:
                yaz.uygula(hedef, {"piyasa": {}})
            except SystemExit as e:
                assert "dokunamaz" in str(e)
            else:
                raise AssertionError("yabancı alan kabul edildi")
            # (b) null siler, boş dizge ezmez
            b, d = yaz.uygula(hedef, {"yorum": ""})
            assert b["yorum"] == "<p>eski</p>" and not d, (b["yorum"], d)
            b, d = yaz.uygula(hedef, {"yorum": None})
            assert b["yorum"] is None and "yorum silindi" in d
            # (c) gündem yaması yayın damgasını 'yazili' yapar; yazı damgası ve sürüm atılır
            b, d = yaz.uygula(hedef, {"gundem": {"kilit": "<p>x</p>"}})
            assert b["gundem_kaynagi"] == "yazili" and b["yazi_surumu"] == 1 and b["yazi_zamani"].endswith("+00:00")
            hedef.write_text(_j.dumps(b), encoding="utf-8")
            b, _ = yaz.uygula(hedef, {"gundem": {"kilit": "<p>y</p>"}})
            assert b["yazi_surumu"] == 2 and b["ilk_yazi_zamani"], b.get("yazi_surumu")
            # (d) damgasız taban sigorta: ölçüm yamadan SONRAYSA red (çıkış 3) — alt süreçle
            yama = Path(td) / "yama.json"; yama.write_text(_j.dumps({"yorum": "<p>z</p>"}), encoding="utf-8")
            eski_mtime = _t.time() - 3600
            _os.utime(yama, (eski_mtime, eski_mtime))
            gelecek = {**b, "olusturma": "2099-01-01T00:00:00+00:00"}
            hedef.write_text(_j.dumps(gelecek), encoding="utf-8")
            kod = _sp.run([sys.executable, "-c",
                           f"import sys; sys.path.insert(0, {str(BURASI)!r}); import yaz; "
                           f"yaz.BULTEN = __import__('pathlib').Path({td!r}); "
                           f"sys.argv = ['yaz.py', {str(yama)!r}, '--tarih', '2026-01-05']; "
                           "raise SystemExit(yaz.main())"],
                          capture_output=True, text=True).returncode
            assert kod == 3, f"mtime sigortası: beklenen 3, gelen {kod}"
            # (e) denetim ENGEL → yazma reddi (çıkış 5); dosya değişmez
            hedef.write_text(_j.dumps(b0), encoding="utf-8")
            kod = _sp.run([sys.executable, "-c",
                           f"import sys; sys.path.insert(0, {str(BURASI)!r}); import yaz; "
                           f"yaz.BULTEN = __import__('pathlib').Path({td!r}); "
                           f"sys.argv = ['yaz.py', {str(yama)!r}, '--tarih', '2026-01-05', '--damgasiz']; "
                           "raise SystemExit(yaz.main())"],
                          capture_output=True, text=True).returncode
            assert kod == 5, f"denetim kapısı: beklenen 5, gelen {kod}"
            assert _j.loads(hedef.read_text(encoding="utf-8"))["yorum"] == "<p>eski</p>", "engelli yama yazıldı"
    sina("yaz.py: yabancı alan reddi · null siler · boş ezmez · yazı damgası/sürümü · mtime sigortası · denetim kapısı", _yaz)
    sina("bicim: sayı yazımı tek kaynak · REDK konumu yön okur · denetim sızıntıyı görür", _bicim)

    for ad in gecen:
        print(f"  ✓ {ad}")
    for ad, hata in dusen:
        print(f"  ✗ {ad}\n      {hata}")
    print(f"\n  {len(gecen)} geçti · {len(dusen)} DÜŞTÜ")
    if dusen:
        print("\n  Bülten katmanlarında sözleşme kayması var. Ağ adımlarına "
              "geçmeden düzeltilmeli.")
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
