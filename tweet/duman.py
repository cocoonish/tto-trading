#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tweet katmanının duman sınaması — ağsız, saniyeler içinde.

Her sigorta kusur geri konarak sınandı: sınır aşımı, HTML sızıntısı, defter
mükerrerliği, bayat koruması, anahtarsız koşunun düşmemesi.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uret  # noqa: E402

SAYAC = {"gecti": 0, "dustu": 0}


def sina(ad: str, fn) -> None:
    try:
        fn()
        SAYAC["gecti"] += 1
        print(f"  ✓ {ad}")
    except KeyboardInterrupt:
        raise
    except BaseException as e:            # SystemExit de bir düşüş, süiti kesmesin
        SAYAC["dustu"] += 1
        print(f"  ✗ {ad}: {type(e).__name__}: {e}")


SAHTE_BULTEN = {
    "tarih": "2026-08-30", "haftalik": True, "gundem_kaynagi": "yazili",
    "yorum": "<p>Piyasa şu <strong>sebeple</strong> böyle hareket etti. " * 40 + "</p>",
    "ozet": {"ne_oldu": "<p>Uzun bir <strong>özet</strong> cümlesi. " * 30 + "</p>",
             "ne_bekleniyor": "Haftaya dört yayım var. " * 20},
    "piyasa": {"en_cok_hareket": {
        "sigma_kip": "haftalik",
        "haftalik": [{"ad": "BIST Bankacılık", "deger": 5.98, "birim": "%"},
                     {"ad": "Brent", "deger": -5.42, "birim": "%"}]}},
    "gostergeler": [{"ad": "USD/TRY", "metin": "48,07", "fark_metin": "+0,19"}],
    # Gündem katmanı TUZAKLI: kilit bölümünün ilk cümlesi siteye atıf yapıyor,
    # ikincisi göndergesi olarak ona yaslanıyor (ikisi de düşmeli), üçüncüsü
    # ayakta kalmalı. tr_makro ise sıra sayısı taşıyor: cümle bölücü "12."de
    # yanılırsa "ayını doldurdu." diye PARÇA üretir.
    "gundem": {
        "kilit": "<p>Ayrıntısı jeopolitik bölümünde duruyor. "
                 "Bu gelişme tam da bu yüzden önemli. "
                 "Hazine Bakanı yeni yaptırım planını açıkladı.</p>",
        "tr_makro": "<p>Sanayi üretimi 12. ayını doldurdu. "
                    "Bugün 10:00'da büyüme verisi geliyor.</p>",
        "global_politika": "<p>Hafta sonunun ağırlık merkezi Hürmüz'dü.</p>",
    },
}

SAHTE_TEKNIK = {
    "tarih": "2026-08-30", "yazili": True,
    "giris": "<p>Dolar haftayı yukarıda kapattı. " * 20 + "</p>",
    "enstrumanlar": [
        {"slug": "xu100", "ad": "BIST 100", "son": 14641.6, "tip": "fiyat",
         "degisim": {"h1": 0.87},
         "dilimler": {"s1": {"yapi": {"sikisma": True}},
                      "gun": {"yapi": {}}}},
        {"slug": "us10y", "ad": "ABD 10 yıllık getiri", "son": 4.72,
         "tip": "getiri", "degisim": {"h1": -1.8},
         "dilimler": {"s1": {"yapi": {}},
                      "gun": {"yapi": {"cift_dip": {"seviye": 4.608}}}}},
    ],
}


def _zincirler():
    """Premium kipi: içerik başına TEK uzun tweet; bölümler, link ve yapı
    bayrakları içinde, HTML dışarıda, tavan aşılmıyor."""
    zb = uret.bulten_zinciri(SAHTE_BULTEN)
    zt = uret.teknik_zinciri(SAHTE_TEKNIK)
    for zincir, ad in ((zb, "bülten"), (zt, "teknik")):
        assert len(zincir) == 1, f"{ad}: {len(zincir)} tweet — tek olmalı"
        t = zincir[0]
        assert 200 < len(t) <= uret.TEK_TAVAN, f"{ad}: {len(t)} karakter"
        assert "<" not in t and ">" not in t.replace("→", ""), \
            f"{ad}: HTML sızdı: {t[:80]}"
        # 30.08 geri bildirimi: link ve emoji YOK — geri sızarsa sınama düşer.
        assert "http" not in t, f"{ad}: link sızdı"
        assert "📰" not in t and "📐" not in t and "•" not in t, f"{ad}: süsleme sızdı"
    assert "Haftanın öne çıkanları" in zb[0] and "Pano:" in zb[0], "bölümler eksik"
    assert "Haftaya" in zb[0], "başlık yok"
    # Gövde ANLATI: yorum varsa o kullanılır (tercüman ilkesi), özet değil.
    assert "sebeple böyle hareket" in zb[0], "gövde yorumdan gelmiyor"
    assert "Uzun bir özet" not in zb[0], "yorum varken özet basıldı"
    yorumsuz = {k: v for k, v in SAHTE_BULTEN.items() if k != "yorum"}
    zb2 = uret.bulten_zinciri(yorumsuz)
    assert "Uzun bir özet" in zb2[0], "yorum yokken özete düşülmedi"
    assert "sıkışma" in zt[0], "yapı bayrağı girmedi"
    assert "çift dip" in zt[0], "çift dip girmedi"
    assert "yatırım tavsiyesi değildir" in zt[0], "sorumluluk notu yok"
    assert "BIST 100" in zt[0] and "ABD 10Y" in zt[0], "kısa adlar kullanılmadı"


def _site_atfi_ve_gundem():
    """31.08 geri bildirimi: tweette siteye/bültene ATIF olmayacak ve gündem
    girecek. Sigorta araçta — kural kaybolursa bu sınama düşer."""
    t = uret.bulten_zinciri(SAHTE_BULTEN)[0]

    # (a) hiçbir site izi kalmadı
    for iz in uret.SITE_IZLERI:
        assert iz not in t.lower(), f"site atfı sızdı: {iz!r}"

    # (b) gündem girdi ve etiketlendi
    assert "Gündem" in t, "gündem bloğu yok"
    assert "Kilit gelişme:" in t and "Türkiye makro:" in t, "gündem etiketi yok"
    assert "Hazine Bakanı yeni yaptırım" in t, "temiz gündem cümlesi düştü"

    # (c) atıf cümlesi VE ona yaslanan öksüz devamı düştü
    assert "bölümünde duruyor" not in t, "atıf cümlesi düşmedi"
    assert "tam da bu yüzden önemli" not in t, "öksüz devam düşmedi"

    # (d) sıra sayısı cümle sanılmadı (parça üretilmedi)
    assert "12. ayını doldurdu" in t, "sıra sayısında cümle bölücü yanıldı"
    assert not re.search(r"(^|\n)[a-zçğıöşü]", t), "küçük harfle başlayan parça"

    # (e) günlük başlık bülteni adıyla anmıyor
    g = uret.bulten_zinciri({**SAHTE_BULTEN, "haftalik": False})[0]
    assert g.startswith("Sabah Notu"), f"günlük başlık: {g[:30]!r}"
    assert "Bülten" not in g, "başlık bülteni adıyla anıyor"


def _kirpma():
    import denetim as dn
    m = "Cümle bir. " * 100
    k = uret._kirp(m, 275)
    assert len(k) <= 275, "kırpma sınırı aşıyor"
    assert k.endswith(".") or k.endswith("…"), f"kırpma ortadan kesti: …{k[-20:]}"
    # (a) 125 karakterlik tam cümle 260'lık pencerede KABUL edilir (eski eşik reddediyordu)
    c1 = "Günün kilit gelişmesi Türkiye'de bir veri değil bir ölçünün geri gelmesiydi ve bu bir ölçünün geri gelmesidir, tamam." 
    c2 = "İkinci cümle uzun uzun anlatır, sonra bir de üçüncüsü gelir ve bunlar hep birlikte iki yüz altmış karakteri kolayca aşar, hiç şüphesiz aşar, kesin aşar."
    k = uret._kirp(c1 + " " + c2, 260)
    assert k == c1, f"tam cümle kabul edilmedi: {k[-40:]!r}"
    # (b) kelime kırpması bağlaçla ya da sayıyla bitmez
    k = uret._kirp("Sabah büyüme geldi ve dolar yükseldi ve faizler düştü ve", 40)
    assert not k.rstrip("…").endswith(" ve"), k
    k = uret._kirp("Banka eylülde %1,25 ve", 20)
    e, _ = dn.denetle("Sabah Notu — 1 Eylül 2026\n\n" + ("Düz cümle. " * 20) + k + "\n\nÖlçüm ve yorumdur; yatırım tavsiyesi değildir.", "bulten")
    assert not any("kırpma" in x for x in e), e
    # (c) etiket ikilemesi
    assert uret._etiketle("Kilit gelişme", "Günün kilit gelişmesi şu.") == "Günün kilit gelişmesi şu."
    assert uret._etiketle("Kilit gelişme", "Hazine ihaleyi iptal etti.").startswith("Kilit gelişme: ")
    # (d) tipografi: aralık ve eksi; yıl-ay korunur
    assert uret._tipografi("bant %1,25-%2,10, fark -0,3, 2024-05'te") == "bant %1,25–%2,10, fark −0,3, 2024-05'te"


def _gonder_sigortalari():
    """gonder.py alt süreçle: anahtarsız düşmez, defter mükerrer önler,
    bayat içerik gönderilmez."""
    kok = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as td:
        bult = Path(td) / "b"; tekn = Path(td) / "t"
        bult.mkdir(); tekn.mkdir()
        bugun = dt.datetime.now(dt.timezone.utc).date().isoformat()
        (bult / f"{bugun}.json").write_text(
            json.dumps({**SAHTE_BULTEN, "tarih": bugun}), encoding="utf-8")
        dun = (dt.datetime.now(dt.timezone.utc).date()
               - dt.timedelta(days=1)).isoformat()
        (bult / f"{dun}.json").write_text(
            json.dumps({**SAHTE_BULTEN, "tarih": dun}), encoding="utf-8")
        defter = Path(td) / "defter.json"

        ortam = {k: v for k, v in dict(**__import__("os").environ).items()
                 if not k.startswith("TW_")}
        # Analiz kanalı da sınama dizinine bakar: gerçek depoda bugün tarihli
        # bir analiz varsa "yeni içerik yok" beklentisini bozardı.
        bos = Path(td) / "analiz-bos"; bos.mkdir()
        yama = ("import uret, analiz; from pathlib import Path; "
                f"uret.BULTENLER = Path({str(bult)!r}); "
                f"uret.TEKNIKLER = Path({str(tekn)!r}); "
                f"analiz.ANALIZ_DIZIN = Path({str(bos)!r}); "
                "import gonder, sys; sys.argv = ['gonder.py'] + "
                "sys.argv[1:]; raise SystemExit(gonder.main())")

        def kos(*ek: str) -> tuple[int, str]:
            s = subprocess.run(
                [sys.executable, "-c", yama, *ek],
                cwd=kok / "tweet", env=ortam, capture_output=True, text=True)
            return s.returncode, s.stdout + s.stderr

        # anahtar yok → kuru koşuya düşer, yeşil biter, zinciri basar
        kod, cikti = kos("--defter", str(defter))
        assert kod == 0, f"anahtarsız koşu düştü: {cikti[-300:]}"
        assert "KURU" in cikti and ("Sabah Notu" in cikti or "Haftaya Bakış" in cikti), cikti[-300:]
        assert not defter.exists(), "kuru koşu deftere yazdı"
        # defterde kayıtlıysa atlanır
        defter.write_text(json.dumps({f"bulten:{bugun}": {"idler": ["1"]}}),
                          encoding="utf-8")
        kod, cikti = kos("--defter", str(defter))
        assert kod == 0 and "yeni içerik yok" in cikti, \
            f"defter mükerrerliği önlemedi: {cikti[-200:]}"
        # bayat: dünün bülteni --tarih verilmeden gönderilMEZ
        defter.write_text("{}", encoding="utf-8")
        kod, cikti = kos("--defter", str(defter))
        assert dun not in cikti, "bayat bülten (dün) bugünkü koşuya girdi"


def _kapi_oge_basina():
    """Kalite kapısı öğe başına: kirli öğe düşer, temiz olan geçer."""
    import gonder
    temiz = ("Sabah Notu — 1 Eylül 2026\n\n" + "Piyasa şu sebeple böyle hareket etti. " * 8
             + "\n\nGündem\nKilit gelişme: bir şey oldu.\n\nÖlçüm ve yorumdur; yatırım tavsiyesi değildir.")
    kirli = temiz.replace("böyle hareket etti.", "böyle hareket etti; bakınız https://x.com/a.")
    gecen, dusen = gonder.kapidan_gecir([("bulten:2026-09-01", [temiz], []),
                                         ("analiz:x", [kirli], [("analiz", "düşen cümle")])])
    assert [k for k, _ in gecen] == ["bulten:2026-09-01"], gecen
    assert [k for k, _ in dusen] == ["analiz:x"], dusen


def _ayna_projeksiyon():
    """Site aynası yalnız kimlik + zaman taşır; iç not ve tohum kaydı sızmaz."""
    import gonder
    d = {"bulten:2026-09-01": {"idler": ["1"], "zaman": "z", "not": "iç not"},
         "analiz:tohum": {"idler": [], "zaman": "", "not": "özel gönderimle atıldı"},
         "bulten:2026-09-02": {"durum": "gönderiliyor", "zaman": "z", "ozet": "abc"}}
    a = gonder._ayna(d)
    assert a == {"bulten:2026-09-01": {"id": "1", "zaman": "z"}}, a


def _jeton_kasasi():
    """oauth2.enc gidiş-dönüşü: TW_KILIT ile yazılan okunur; yanlış kilitle
    açma denemesi net hatayla düşer (sessizce bozuk jeton dönmez)."""
    import os
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gonder
    with tempfile.TemporaryDirectory() as td:
        dosya = Path(td) / "oauth2.enc"
        os.environ["TW_KILIT"] = "sinama-parolasi-123"
        dosya.write_bytes(gonder._kilit().encrypt(b"jeton-abc"))
        assert gonder._refresh_oku(dosya) == "jeton-abc", "jeton gidiş-dönüşü bozuk"
        os.environ["TW_KILIT"] = "BASKA-parola"
        try:
            gonder._refresh_oku(dosya)
        except SystemExit as e:
            assert "çözülemedi" in str(e), f"yanlış kilit mesajı belirsiz: {e}"
        else:
            raise AssertionError("yanlış kilit sessizce kabul edildi")
        del os.environ["TW_KILIT"]


SAHTE_ANALIZ_MDX = """---
title: '2 Eylül 2026 Sınama Yazısı — yönetici özetinden gönderi'
description: 'Sınama açıklaması.'
pubDate: 2026-09-02
tags: ['sinama']
durum: 'aktif'
kaynak: 'sentetik'
ozet: 'Sınama tezi tek cümle.'
seviye: 'orta'
onkosul: []
---

import Deger from '../../components/Deger.astro';

<div class="yonetici">
  <span class="etiket">Yönetici özeti</span>

  <p class="tez">Bu yazı ölçümü anlatıyor. Merkez
  %<Deger proje="sinama" anahtar="merkez" ondalik={2}>9,99</Deger> ve
  fark <Deger proje="sinama" anahtar="fark" ondalik={1} isaret={true}>+0,1</Deger> puan.</p>

  <table>
    <tbody>
      <tr><td>Gelir mi</td><td>Evet, %<Deger proje="sinama" anahtar="merkez" ondalik={2}>9,99</Deger>. Ayrıntısı yukarıdaki grafikte duruyor.</td></tr>
      <tr><td>Kanıtın gücü</td><td><b>Orta.</b> Örneklem 31 ay.</td></tr>
    </tbody>
  </table>

  <ul class="rakamlar">
    <li><b>%<Deger proje="sinama" anahtar="merkez" ondalik={2}>9,99</Deger></b><span>birleşik merkez</span></li>
    <li><b><Deger proje="sinama" anahtar="yok" ondalik={2}>0,42</Deger></b><span>bulunamayan anahtar yedeğiyle</span></li>
  </ul>
</div>

Gövde.

## Ne ölçmedik

Bir şey.
"""


def _analiz_zinciri():
    """Analiz gönderisi yönetici özetinden kurulur; <Deger> canlı çözülür,
    sayfa mobilyasına atıf yapan cümle düşer, sorumluluk notu kalır."""
    import analiz as an
    with tempfile.TemporaryDirectory() as td:
        kok = Path(td)
        (kok / "analiz").mkdir()
        (kok / "analiz" / "sinama-yazisi-2026-09-02.mdx").write_text(SAHTE_ANALIZ_MDX, encoding="utf-8")
        (kok / "ozet" / "sinama").mkdir(parents=True)
        (kok / "ozet" / "sinama" / "ozet.json").write_text(
            json.dumps({"merkez": 1.4849, "fark": -0.36}), encoding="utf-8")
        eski = (an.ANALIZ_DIZIN, an.OZET_DIZIN)
        an.ANALIZ_DIZIN, an.OZET_DIZIN = kok / "analiz", kok / "ozet"
        an._OZET_ONBELLEK.clear()
        try:
            yazilar = an.bugunun_analizleri(dt.date(2026, 9, 2))
            assert len(yazilar) == 1, f"bugünün analizi bulunamadı: {len(yazilar)}"
            assert not an.bugunun_analizleri(dt.date(2026, 9, 1)), "bayat koruması: dünkü tarih yazı döndürdü"
            t = an.analiz_zinciri(yazilar[0])[0]
        finally:
            an.ANALIZ_DIZIN, an.OZET_DIZIN = eski
            an._OZET_ONBELLEK.clear()
    assert t.startswith("Analiz — 2 Eylül 2026\nSınama Yazısı"), t[:60]
    assert "%1,48" in t and "9,99" not in t, "canlı değer çözülmedi (yedek kaldı)"
    assert "−0,4 puan" in t, f"isaretli/eksi biçimi yanlış: {t[:400]}"
    assert "0,42" in t, "bulunamayan anahtarın yedeği kalmadı"
    assert "GELİR Mİ." in t and "KANITIN GÜCÜ." in t, "tablo satırları Türkçe büyük harfle etiketlenmedi"
    assert "yukarıdaki grafikte" not in t, "sayfa mobilyasına atıf düşmedi"
    assert "Evet, %1,48." in t, "atıf cümlesi düşerken komşu cümle kayboldu"
    assert "Kilit ölçümler — birleşik merkez: %1,48" in t, "rakam şeridi yok"
    assert t.endswith("Analizdir; yatırım tavsiyesi değildir."), "sorumluluk notu sonda değil"
    assert "<" not in t and "Deger" not in t, "etiket sızdı"


def _denetim():
    """Kalite kapısı: her sigorta kusur geri konarak sınanır."""
    import denetim as dn
    temiz = ("Sabah Notu — 1 Eylül 2026\n\n" + "Piyasa bugün şu sebeple böyle hareket etti. " * 8
             + "\n\nGünün öne çıkanları: Brent −%1,20 · BIST 100 +%0,40"
             + "\n\nÖlçüm ve yorumdur; yatırım tavsiyesi değildir.")
    e, u = dn.denetle(temiz, "bulten")
    assert not e, f"temiz metin engel üretti: {e}"
    def engel(m, iz):
        e, _ = dn.denetle(m, "bulten")
        assert any(iz in x for x in e), f"{iz!r} yakalanmadı: {e}"
    engel(temiz.replace("böyle hareket etti.", "böyle hareket etti, alın."), "tavsiye")
    engel(temiz + " https://x.com/a", "link")
    for lnk in ("cocoonish.github.io", "x.com/i/status/1", "www.tcmb.gov.tr", "[oku](https://a.b)", "t.co/abc", "tcmb.gov.tr/x"):
        engel(temiz.replace("Brent", f"Brent ({lnk})"), "link")
    for masum in ("A.Ş. bilançosu", "vb. Bu", "%1,25 ile %2,10 arası.", "TL 48,17.", "ör. TCMB", "2026-09-01"):
        e0, _ = dn.denetle(temiz.replace("Brent", f"Brent {masum}"), "bulten")
        assert not any("link" in x for x in e0), f"{masum!r} link sanıldı: {e0}"
    import gonder as gd
    try:
        gd._gonder_zincir(["Sabah Notu\n\nMetin https://x.com/a"], "sahte-jeton")
    except SystemExit as ex:
        assert "link" in str(ex), f"gönderim kilidi yanlış sebeple durdu: {ex}"
    else:
        raise AssertionError("gönderim katmanı linkli zinciri durdurmadı")
    engel(temiz.replace("Brent", "<b>Brent</b>"), "HTML")
    engel(temiz.replace("Brent", "bu sayfadaki Brent"), "atıf")
    engel(temiz.replace("Ölçüm ve yorumdur; yatırım tavsiyesi değildir.", "Bitti."), "sorumluluk")
    engel(temiz.replace("BIST 100 +%0,40", "BIST 100 +%0,…"), "kırpma")
    engel(temiz.replace("Günün öne çıkanları: Brent −%1,20 · BIST 100 +%0,40", "Pano:"), "içeriksiz")
    engel(temiz.replace("hareket etti.", "ozet.json'dan okundu."), "okura değil")
    engel("Kısa.", "kısa")
    engel(temiz + " " + ("x" * 4000), "uzun")
    _, u = dn.denetle(temiz.replace("−%1,20", "-%1,20"), "bulten")
    assert any("ASCII" in x for x in u), f"ASCII tire uyarısı yok: {u}"
    _, u = dn.denetle(temiz.replace("Brent", "İTO yukarıda geliyor, Brent"), "analiz")
    assert any("yukarıda" in x for x in u), "belirsiz atıf uyarı vermedi"
    e, _ = dn.denetle(temiz.replace("Brent", "yukarıdaki tabloda Brent"), "analiz")
    assert any("mobilya" in x for x in e), f"'yukarıdaki tablo' engel üretmedi: {e}"
    e, _ = dn.denetle(temiz.replace("Sabah Notu — 1 Eylül 2026", "Günaydın piyasa"), "bulten")
    assert any("başlık satırı" in x for x in e), f"başlıksız bülten gönderisi geçti: {e}"
    _, u = dn.denetle(temiz.replace("−%1,20", "%1,20-%1,40"), "bulten")
    assert any("aralık tiresi" in x for x in u), f"aralık tiresi uyarısı yok: {u}"
    _, u = dn.denetle(temiz.replace("Brent −%1,20", "Brent −%1,20 ve TL %37,00 ile %2,80")
                      + "\n\nGündem: fonlama %37,00 ve büyüme %2,80 açıklandı.", "bulten")
    assert any("aynı sayıları" in x for x in u), f"ortak sayı uyarısı yok: {u}"
    assert dn.EN_COK == __import__("uret").TEK_TAVAN, "tavan tek kaynak değil"
    import uret as ur
    assert not ur._site_izi_var("TCMB haftalık bülteninde menkul kıymet stoku arttı."), "gerçek bilgi düştü"
    assert ur._site_izi_var("Bu bültenin cevaplaması gereken soru şu."), "öz-atıf düşmedi"
    assert ur._site_izi_var("Ayrıntı aşağıda açıkça yazılır."), "'aşağıda açıkça' düşmedi"


def _kapanis_notu():
    """Sorumluluk notu her gönderinin SON satırı ve kırpmadan muaf."""
    zb = uret.bulten_zinciri(SAHTE_BULTEN)[0]
    zt = uret.teknik_zinciri(SAHTE_TEKNIK)[0]
    assert zb.endswith(uret.SORUMLULUK_BULTEN), zb[-80:]
    assert zt.endswith(uret.SORUMLULUK_TEKNIK), zt[-80:]
    # gövde tavanı aşsa bile not kalır
    sisman = {**SAHTE_BULTEN, "yorum": "<p>Uzun uzun anlatı cümlesi burada. </p>" * 400}
    z = uret.bulten_zinciri(sisman)[0]
    assert len(z) <= uret.TEK_TAVAN and z.endswith(uret.SORUMLULUK_BULTEN), (len(z), z[-60:])
    import denetim as dn
    for z_, tur in ((zb, "bulten"), (zt, "teknik")):
        e, _ = dn.denetle(z_, tur)
        assert not e, f"{tur} zinciri kendi kapısından geçmedi: {e}"


def main() -> int:
    print("tweet duman sınaması:")
    sina("analiz gönderisi: yönetici özeti, canlı <Deger>, atıf düşer, not sonda", _analiz_zinciri)
    sina("kalite kapısı: tavsiye · link · HTML · atıf · kesik · boş etiket · dil · uzunluk", _denetim)
    sina("sorumluluk notu her gönderide, kırpmadan muaf", _kapanis_notu)
    sina("zincirler: uzunluk, HTML sızıntısı, link, yapı bayrağı", _zincirler)
    sina("site atfı yok · gündem girdi · öksüz cümle düştü",
         _site_atfi_ve_gundem)
    sina("kırpma cümle sınırında", _kirpma)
    sina("gonder: anahtarsız yeşil, defter mükerrerliği, bayat koruması",
         _gonder_sigortalari)
    sina("jeton kasası: şifreli gidiş-dönüş, yanlış kilit düşer", _jeton_kasasi)
    sina("kalite kapısı öğe başına: kirli düşer, temiz geçer", _kapi_oge_basina)
    sina("defter aynası projeksiyon: yalnız kimlik + zaman", _ayna_projeksiyon)
    print(f"\n  {SAYAC['gecti']} geçti · {SAYAC['dustu']} DÜŞTÜ")
    return 1 if SAYAC["dustu"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
