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
        assert kod in (0, 1, 2, 3), f"beklenmeyen zincir kodu: {kod}"
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
