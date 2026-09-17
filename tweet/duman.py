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


def _siteye_sizinti_yok():
    """Gönderim katmanı SİTEYE hiçbir şey yazmaz.

    Defter bir zamanlar site/src/data/tweet/defter.json'a aynalanıyordu ve sayfa
    künyesi oradan "X gönderisi ↗" bağı kuruyordu. Site X gönderisini artık
    okura göstermiyor; ayna da yazılmıyor. Sınama iki şeyi birden sorar, çünkü
    biri düşerse öbürü sessizce geri gelir: kaynakta site yoluna yazan bir sabit
    kalmadı VE gerçek bir defter yazımı site ağacına dokunmuyor.
    """
    import gonder
    import io, tokenize
    ham = Path(gonder.__file__).read_text(encoding="utf-8")
    # YORUMLAR ÇIKARILIR: bu dosyanın kendi açıklama satırı yolu ANIYOR ve
    # ham metinde arayan bir ölçüt kendi belgesine takılır. Ölçülen şey KOD.
    kod = "".join(t.string for t in tokenize.generate_tokens(io.StringIO(ham).readline)
                  if t.type != tokenize.COMMENT).replace("\\", "/")
    assert "DEFTER_AYNA" not in kod, "gönderim katmanında site aynası sabiti geri gelmiş"
    assert "src/data/tweet" not in kod, "gönderim katmanı site/src/data/tweet yoluna yazıyor"
    assert '"site"' not in kod and "'site'" not in kod, \
        "gönderim katmanı site ağacında bir yol kuruyor"

    site_tweet = gonder.KOK / "site" / "src" / "data" / "tweet"
    vardi = site_tweet.exists()
    with tempfile.TemporaryDirectory() as gecici:
        yol = Path(gecici) / "defter.json"
        gonder._defter_yaz(yol, {"bulten:2026-09-01": {"idler": ["1"], "zaman": "z"}})
        assert yol.exists(), "defter yazılmadı"
    assert site_tweet.exists() == vardi, "defter yazımı site ağacına dokundu"


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
    """Analiz gönderisi yönetici özetinden kurulur; <Deger> SABİT yedek metniyle
    gider (sayfa ne gösteriyorsa — karar 08.09.2026, canlı çözüm yok), sayfa
    mobilyasına atıf yapan cümle düşer, sorumluluk notu kalır."""
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
    # ozet.json'da merkez=1,4849 duruyor ama gönderi SAYFAYI izler: yedek 9,99 kalır.
    assert "%9,99" in t and "1,48" not in t, f"analiz sayısı canlı çözüldü — sayfa sabit, gönderi ayrıştı: {t[:300]}"
    assert "+0,1 puan" in t and "−0,4" not in t, f"işaretli yedek metin korunmadı: {t[:400]}"
    assert "0,42" in t, "bulunamayan anahtarın yedeği kalmadı"
    assert "Evet, %9,99." in t, "atıf cümlesi düşerken komşu cümle kayboldu"
    assert "GELİR Mİ." in t and "KANITIN GÜCÜ." in t, "tablo satırları Türkçe büyük harfle etiketlenmedi"
    assert "yukarıdaki grafikte" not in t, "sayfa mobilyasına atıf düşmedi"
    assert "Kilit ölçümler — birleşik merkez: %9,99" in t, "rakam şeridi yok (sabit yedek metin beklenir)"
    assert t.endswith("Analizdir; yatırım tavsiyesi değildir."), "sorumluluk notu sonda değil"
    assert "<" not in t and "Deger" not in t, "etiket sızdı"


def _tavan_asiminda_rakam_seridi():
    """Tavanı AŞAN bir özet: tablo satırları SONDAN düşer, rakam şeridi KALIR.

    17.09.2026'da ölçüldü — `_kapat` gövdeyi tavana kırpıyor, yani `_metin()`
    tanımı gereği tavanı AŞAMAZ; döngü ölçüyü ondan okuduğu sürece koşulu hiç
    sağlanmaz ve kısaltma kodu ÖLÜDÜR. O hâlde kırpma sondan yer ve tam da
    korunmak istenen şerit sessizce gider: gönderi doğru görünür, yalnız en
    alıntılanabilir bloğu yoktur ve hiçbir kapı bunu sormuyordu. Ölçü artık
    KIRPILMAMIŞ gövdeden alınır; bu madde onu arızaya karşı sabitler.
    """
    import analiz as an
    import uret as ur
    dolgu = "Ölçülen sayı bu satırda duruyor ve cümle yeterince uzundur. " * 6
    satirlar = [(f"Soru {i}", dolgu) for i in range(1, 10)]
    rakamlar = [(f"%{i},0", f"ölçüm {i}") for i in range(1, 8)]
    sahte = {"tez": "Tez cümlesi. " * 60, "satirlar": satirlar, "rakamlar": rakamlar}
    eski = an.yonetici_ozeti
    an.yonetici_ozeti = lambda _govde: sahte
    try:
        t = an.analiz_zinciri({"slug": "sinama-2026-09-17", "govde": "",
                               "title": "17 Eylül 2026 Sınama — alt başlık",
                               "pubDate": "2026-09-17"})[0]
    finally:
        an.yonetici_ozeti = eski
    assert len(t) <= ur.TEK_TAVAN, f"tavan aşıldı: {len(t)}"
    assert "Kilit ölçümler —" in t, "tavan aşımında rakam şeridi DÜŞTÜ — kırpma sondan yemiş"
    assert t.endswith("Analizdir; yatırım tavsiyesi değildir."), "sorumluluk notu sonda değil"
    assert "Tez cümlesi." in t, "tez düştü — kısaltma ortadan değil baştan yemiş"
    # Satırlar SONDAN düşer: ilk satır durur, son satır durmaz.
    assert "SORU 1." in t, "ilk tablo satırı düştü"
    assert "SORU 9." not in t, "hiçbir satır düşmemiş — kısaltma hiç çalışmadı"


def _denetim():
    """Kalite kapısı: her sigorta kusur geri konarak sınanır."""
    import denetim as dn
    import uret as ur
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
    for lnk in ("cocoonish.github.io", "x.com/i/status/1", "www.tcmb.gov.tr", "[oku](https://a.b)", "t.co/abc", "tcmb.gov.tr/x",
                "cocoonish.github.io'da", "bloomberght.com’da", "tcmb.gov.tr…", "bloomberght.com—", "X.com/a",
                "Bloomberg.com'a göre", "Reuters.com", "COCOONISH.GITHUB.IO", "Investing.com", "boj.or.jp", "kur.de/x", "x．com"):
        engel(temiz.replace("Brent", f"Brent ({lnk})"), "link")
    for masum in ("A.Ş. bilançosu", "vb. Bu", "%1,25 ile %2,10 arası.", "TL 48,17.", "ör. TCMB", "2026-09-01",
                  "ettik.Biz de", "kapandı.Me", "TCMB.de", "T.C. Hazine", "14.30'da", "1.000 TL", "1.tr", "S&P 500"):
        e0, _ = dn.denetle(temiz.replace("Brent", f"Brent {masum}"), "bulten")
        assert not any("link" in x for x in e0), f"{masum!r} link sanıldı: {e0}"
    for zayif in ("kur.de", "riksbank.se", "snb.ch"):     # tek etiket + ülke kodu: uyarı, engel değil
        e0, u = dn.denetle(temiz.replace("Brent", f"Brent {zayif} yükseldi,"), "bulten")
        assert not any("link" in x for x in e0) and any("alan adına benzeyen" in x for x in u), f"{zayif}: {e0} {u}"
    e, _ = dn.denetle(temiz.replace("Brent", "Brent ⏰ 10:00 •"), "bulten")
    assert any("emoji" in x for x in e), f"⏰/• emoji engeli yok: {e}"
    assert ur._duz("<p>S&amp;P 500 &nbsp;yükseldi</p>") == "S&P 500 yükseldi", ur._duz("<p>S&amp;P 500 &nbsp;yükseldi</p>")
    assert ur._tipografi("2026-09-01'e göre 3-5 gün") == "2026-09-01'e göre 3–5 gün", ur._tipografi("2026-09-01'e göre 3-5 gün")
    import subprocess as _sp, sys as _sys
    cikti = _sp.run([_sys.executable, "-c", "import sys; sys.path.insert(0, 'tweet'); import denetim, uret; print(uret.__file__)"],
                    capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[1]))
    assert cikti.stdout.strip().endswith("tweet/uret.py"), f"denetim tek başına yüklenince uret gölgelendi: {cikti.stdout} {cikti.stderr[-200:]}"
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
    _, u = dn.denetle(temiz.replace("Brent", "Brent (2026-09-01 kapanışı, 2026-08-31'e göre)"), "bulten")
    assert not any("aralık tiresi" in x for x in u), f"ISO tarih aralık tiresi sanıldı: {u}"
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


def _ozel_anahtar():
    """Özel gönderinin defter anahtarı araç kanalıyla aynı biçimde türetilir; kökteki
    günde yayımlanan analiz varken serbest başlıklı kök ozel: yedeğine SESSİZCE düşmez."""
    import ozel
    import analiz as an
    kok = Path(__file__).resolve().parents[1]
    P_ = Path
    assert ozel.anahtar_turet(P_("x/bulten-2026-08-31.txt"), "Sabah Notu — 31 Ağustos 2026", "bulten", True) == "bulten:2026-08-31"
    assert ozel.anahtar_turet(P_("x/haftaya.txt"), "Haftaya Bakış — 6 Eylül 2026", "bulten", True) == "bulten:2026-09-06"
    aktif = [a for a in an.analizler() if str(a.get("durum", "aktif")) == "aktif" and str(a.get("pubDate", ""))[:10]]
    assert aktif, "sınama için yayımda analiz yok"
    slug = aktif[0]["slug"]
    assert ozel.anahtar_turet(P_(f"x/{slug}.txt"), "Serbest başlık", "ozel", True) == f"analiz:{slug}"
    gun = str(aktif[0]["pubDate"])[:10]
    try:
        ozel.anahtar_turet(P_(f"x/serbest-kok-{gun}.txt"), "Serbest başlık", "ozel", True)
        raise AssertionError("analiz gününde serbest kök ozel: ile geçti")
    except SystemExit as ex:
        assert "analiz" in str(ex) and "--anahtar" in str(ex), str(ex)
    assert ozel.anahtar_turet(P_(f"x/serbest-kok-{gun}.txt"), "Serbest başlık", "ozel", False) == f"ozel:serbest-kok-{gun}"
    assert ozel.anahtar_turet(P_("x/kredi-2020-01-04.txt"), "Serbest başlık", "ozel", True) == "ozel:kredi-2020-01-04"
    try:
        ozel.anahtar_turet(P_("x/yok-boyle-slug.txt"), "Analiz — 1 Eylül 2026", "analiz", True)
        raise AssertionError("eşleşmeyen analiz kökü geçti")
    except SystemExit as ex:
        assert "analiz:<slug>" in str(ex)


def main() -> int:
    print("tweet duman sınaması:")
    sina("analiz gönderisi: yönetici özeti, SABİT <Deger>, atıf düşer, not sonda", _analiz_zinciri)
    sina("kalite kapısı: tavsiye · link · HTML · atıf · kesik · boş etiket · dil · uzunluk", _denetim)
    sina("sorumluluk notu her gönderide, kırpmadan muaf", _kapanis_notu)
    sina("zincirler: uzunluk, HTML sızıntısı, link, yapı bayrağı", _zincirler)
    sina("site atfı yok · gündem girdi · öksüz cümle düştü",
         _site_atfi_ve_gundem)
    sina("kırpma cümle sınırında", _kirpma)
    sina("tavan aşımında satır düşer, rakam şeridi kalır", _tavan_asiminda_rakam_seridi)
    sina("gonder: anahtarsız yeşil, defter mükerrerliği, bayat koruması",
         _gonder_sigortalari)
    sina("jeton kasası: şifreli gidiş-dönüş, yanlış kilit düşer", _jeton_kasasi)
    sina("kalite kapısı öğe başına: kirli düşer, temiz geçer", _kapi_oge_basina)
    sina("gönderim katmanı siteye yazmıyor (X aynası kaldırıldı)", _siteye_sizinti_yok)
    sina("özel gönderi anahtarı: araç kanalıyla aynı biçim, analiz gününde sessiz ozel: yok", _ozel_anahtar)
    print(f"\n  {SAYAC['gecti']} geçti · {SAYAC['dustu']} DÜŞTÜ")
    return 1 if SAYAC["dustu"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
