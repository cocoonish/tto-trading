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
