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
                     {"ad": "Brent", "deger": -5.42, "birim": "%"}],
        # Olağandışı satırı sayfanın σ listesinden kurulur (05.10.2026).
        "sigma": [{"ad": "BIST Bankacılık", "deger": 5.98, "birim": "%", "sigma": 2.4},
                  {"ad": "Brent", "deger": -5.42, "birim": "%", "sigma": -1.6}]}},
    "gostergeler": [{"ad": "USD/TRY", "metin": "48,07", "fark_metin": "+0,19", "fark_birim": "%",
                     "bugun_yeni": True}],
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

def _zincirler():
    """Premium kipi: içerik başına TEK uzun tweet; bölümler, link ve yapı
    bayrakları içinde, HTML dışarıda, tavan aşılmıyor."""
    zb = uret.bulten_zinciri(SAHTE_BULTEN)
    for zincir, ad in ((zb, "bülten"),):
        assert len(zincir) == 1, f"{ad}: {len(zincir)} tweet — tek olmalı"
        t = zincir[0]
        assert 200 < len(t) <= uret.TEK_TAVAN, f"{ad}: {len(t)} karakter"
        assert "<" not in t and ">" not in t.replace("→", ""), \
            f"{ad}: HTML sızdı: {t[:80]}"
        # 30.08 geri bildirimi: link ve emoji YOK — geri sızarsa sınama düşer.
        assert "http" not in t, f"{ad}: link sızdı"
        assert "📰" not in t and "📐" not in t and "•" not in t, f"{ad}: süsleme sızdı"
    assert "Haftanın olağandışı hareketleri" in zb[0] and "Pano:" in zb[0], "bölümler eksik"
    assert "BIST Bankacılık +%5,98 (+2,4σ)" in zb[0] and "Brent" not in zb[0].split("olağandışı")[-1].split("\n")[0], \
        "olağandışı satırı σ listesinden ve eşikle kurulmadı"
    assert "Haftaya" in zb[0], "başlık yok"
    # Gövde ANLATI: yorum varsa o kullanılır (tercüman ilkesi), özet değil.
    assert "sebeple böyle hareket" in zb[0], "gövde yorumdan gelmiyor"
    assert "Uzun bir özet" not in zb[0], "yorum varken özet basıldı"
    yorumsuz = {k: v for k, v in SAHTE_BULTEN.items() if k != "yorum"}
    zb2 = uret.bulten_zinciri(yorumsuz)
    assert "Uzun bir özet" in zb2[0], "yorum yokken özete düşülmedi"
    # Teknik zinciri 01.10.2026'da çıktı (yayın sona erdi); geri gelmesin.
    assert not hasattr(uret, "teknik_zinciri") and not hasattr(uret, "yazilmis_teknik"), \
        "sona eren teknik zinciri tweet üreticisine geri dönmüş"


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
    # (b) "…" ÜRETİLMEZ (05.10.2026; eski sözleşme "temiz '…' kırpması kapıdan
    #     geçer"di): sığmayan tek cümle bütünüyle düşer, ortasından kesilmez.
    k = uret._kirp("Sabah büyüme geldi ve dolar yükseldi ve faizler düştü ve", 40)
    assert k == "", f"sığmayan birim kesildi: {k!r}"
    k = uret._kirp("Banka eylülde %1,25 ve", 20)
    assert k == "" and "…" not in k, k
    e, _ = dn.denetle("Sabah Notu — 1 Eylül 2026\n\n" + ("Düz cümle. " * 20) + "\n\nÖlçüm ve yorumdur; yatırım tavsiyesi değildir.", "bulten")
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
        bult = Path(td) / "b"
        bult.mkdir()
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
    # A8 (05.10.2026): başlık kaynaktaki cümle düzeninde; soru "?" ile, isim
    # öbeği iki noktayla — büyük harfli "GELİR Mİ." artık bir kusurdur.
    assert "Gelir mi? Evet, %9,99." in t, f"soru başlığı cümle düzeninde ve '?' ile değil: {t[:500]}"
    assert "Kanıtın gücü: Orta. Örneklem 31 ay." in t, f"isim öbeği başlık iki noktayla değil: {t[:500]}"
    assert "GELİR" not in t and "KANITIN" not in t, "başlık büyük harfe çevrildi"
    assert "yukarıdaki grafikte" not in t, "sayfa mobilyasına atıf düşmedi"
    # Şerit yalnız metinde GEÇMEYEN ölçümü taşır, değer önde: %9,99 tezde ve
    # satırda geçiyor (şeride girmez), 0,42 hiçbir yerde yok (girer).
    assert "Kilit ölçüm: 0,42 — bulunamayan anahtar yedeğiyle" in t, f"şerit değer önde ve tekrarsız değil: {t[-300:]}"
    assert "birleşik merkez" not in t and t.count("%9,99") == 2, "metinde geçen değer şeride ikinci kez girdi"
    assert "…" not in t, "analiz gönderisinde '…'"
    assert t.endswith("Analizdir; yatırım tavsiyesi değildir."), "sorumluluk notu sonda değil"
    assert "<" not in t and "Deger" not in t, "etiket sızdı"


def _tavan_asiminda_rakam_seridi():
    """Tavanı AŞAN bir özet: tablo satırları SONDAN düşer, tez kalır; şerit
    her adımda KALAN metne karşı yeniden kurulur.

    17.09.2026'da ölçüldü — `_kapat` gövdeyi tavana kırpıyor, yani kırpılmış
    metin tanımı gereği tavanı AŞAMAZ; döngü ölçüyü ondan okuduğu sürece
    koşulu hiç sağlanmaz ve kısaltma kodu ÖLÜDÜR; kırpma sondan yer. Ölçü
    KIRPILMAMIŞ gövdeden alınır. 05.10.2026'dan beri (A8) şerit yalnız metinde
    geçmeyen ölçümü taşır: gövdede kalan satırın sayısı şeride girmez, tavan
    yüzünden DÜŞEN satırın sayısı şeride DÖNER (ölçüm gönderiden kaybolmaz),
    hiçbir yerde geçmeyen sayı kalır.
    """
    import analiz as an
    import uret as ur
    dolgu = "Ölçülen sayı bu satırda duruyor ve cümle yeterince uzundur. " * 6
    satirlar = [(f"Soru {i}", f"Satırın kendi ölçümü %{i}0,5 düzeyinde. " + dolgu) for i in range(1, 10)]
    rakamlar = [("%10,5", "ilk satırın ölçümü"), ("%90,5", "son satırın ölçümü"),
                ("%77,7", "hiçbir yerde geçmeyen ölçüm")]
    sahte = {"tez": "Tez cümlesi %1,25 taşır. " + "Tez cümlesi. " * 60, "satirlar": satirlar, "rakamlar": rakamlar}
    eski = an.yonetici_ozeti
    an.yonetici_ozeti = lambda _govde: sahte
    try:
        t = an.analiz_zinciri({"slug": "sinama-2026-09-17", "govde": "",
                               "title": "17 Eylül 2026 Sınama — alt başlık",
                               "pubDate": "2026-09-17"})[0]
        dusen = list(ur.DUSEN)
    finally:
        an.yonetici_ozeti = eski
    assert len(t) <= ur.TEK_TAVAN, f"tavan aşıldı: {len(t)}"
    assert "…" not in t, "tavan aşımında '…' üretildi"
    assert t.endswith("Analizdir; yatırım tavsiyesi değildir."), "sorumluluk notu sonda değil"
    assert "Tez cümlesi %1,25 taşır." in t, "tez düştü — kısaltma ortadan değil baştan yemiş"
    # Satırlar SONDAN düşer: ilk satır durur, son satır durmaz.
    assert "Soru 1: Satırın kendi ölçümü %10,5" in t, "ilk tablo satırı düştü"
    assert "Soru 9:" not in t, "hiçbir satır düşmemiş — kısaltma hiç çalışmadı"
    assert any(b == "analiz-bütçe" and c.startswith("Soru 9:") for b, c in dusen), \
        f"tavan yüzünden düşen satır DUSEN'de görünmüyor: {dusen[:3]}"
    serit = [b for b in t.split("\n\n") if b.startswith("Kilit ölçüm")]
    assert serit, "şerit yok — düşen satırın ölçümü gönderiden kayboldu"
    assert "%90,5 — son satırın ölçümü" in serit[0], f"düşen satırın ölçümü şeride dönmedi: {serit[0]}"
    assert "%77,7 — hiçbir yerde geçmeyen ölçüm" in serit[0], f"metinde geçmeyen ölçüm şeritte yok: {serit[0]}"
    assert "ilk satırın ölçümü" not in serit[0] and t.count("%10,5") == 1, \
        f"gövdede kalan satırın ölçümü şeride ikinci kez girdi: {serit[0]}"


def _a8_baslik_duzeni():
    """A8: soru sütunu kaynaktaki cümle düzeninde kalır. "?" YALNIZ soru
    biçimindeki başlığa (soru eki ya da soru sözcüğü), isim öbeği iki noktayla.
    Arşivdeki 58 başlığın 15'i isim öbeği; kör bir "?" kuralı "Kanıtın gücü?
    Orta." üretirdi."""
    import analiz as an
    beklenen = {
        "Gelir mi": "Gelir mi? x", "Kanıtın gücü": "Kanıtın gücü: x",
        "Bu toplantıda artırım gelir mi": "Bu toplantıda artırım gelir mi? x",
        "Ön ucun alanı kaldı mı": "Ön ucun alanı kaldı mı? x", "Geçen yılın programı tuttu mu": "Geçen yılın programı tuttu mu? x",
        "Ne zaman": "Ne zaman? x", "Nereye kadar": "Nereye kadar? x", "Neden tek hafta": "Neden tek hafta? x",
        "Borçlanmanın yarısı nereden": "Borçlanmanın yarısı nereden? x", "Euroya nasıl geçti": "Euroya nasıl geçti? x",
        "Yıl sonları kaça denk geliyor": "Yıl sonları kaça denk geliyor? x", "Hangi kural": "Hangi kural? x",
        "Faize etkisi": "Faize etkisi: x", "Katalizörler": "Katalizörler: x", "Faiz — Fed": "Faiz — Fed: x",
        "İran savaşında son durum": "İran savaşında son durum: x", "Türkiye'ye faturası": "Türkiye'ye faturası: x",
        "Sonraki adımın koşulu": "Sonraki adımın koşulu: x", "Hareketin büyüklüğü": "Hareketin büyüklüğü: x",
        "Eşik olasılıkları": "Eşik olasılıkları: x",
        "Fark şu an nerede?": "Fark şu an nerede? x", "Kanıtın gücü.": "Kanıtın gücü: x",
    }
    yanlis = {k: an.baslikli_satir(k, "x") for k, v in beklenen.items() if an.baslikli_satir(k, "x") != v}
    assert not yanlis, f"başlık düzeni yanlış: {yanlis}"
    assert not hasattr(an, "_buyuk_tr"), "büyük harf çevirisi geri kondu"


def _a8_serit():
    """A8 rakam şeridi: yalnız metinde GEÇMEYEN ölçüm, değer önde, etiket
    kırpılmaz, bileşik kalem ikili ikili eşlenir (kalem ayracı "; "), boş
    şerit hiç basılmaz (boş etiket kapıda ENGEL'dir)."""
    import analiz as an
    import denetim as dn
    metin = ("Politika faizi %37,0; 1 yıl ile politika arasındaki 207 baz puanın kaynağı ayrıştırılmadı. "
             "12 Mart toplantısı. Reel faiz %−3,41 ve 22,1 puan.")
    k, atlanan = an.serit_kalemleri([
        ("%37,0", "politika faizi"),                       # metinde: düşer
        ("+207 bp", "1 yıllık − politika"),                # "207 baz puanın": ekli birim aynı ölçüm, düşer
        ("−12 bp", "6 aylık düğüm"),                       # "12 Mart" ölçüm değil: kalır
        ("−%3,41", "sapma"),                               # "%−3,41" aynı ölçüm (işaret sırası farklı): düşer
        ("−22,1 puan", "eksi makas"),                      # metinde +22,1: işaret sayının parçası, kalır
        ("%10,76 · %4,17", "reel faiz: ankete göre · gerçekleşene göre"),   # metinde yok: eşlenir, kalır
        ("%1 · %2 · %3", "tek · iki"),                     # eşlenemez: atlanır
        ("6/7", "paragraf aynı"),                          # metinde yok: kalır
    ], metin)
    assert k == ["−12 bp — 6 aylık düğüm", "−22,1 puan — eksi makas",
                 "%10,76 — reel faiz: ankete göre · %4,17 — gerçekleşene göre", "6/7 — paragraf aynı"], k
    assert atlanan and "%1 · %2 · %3" in atlanan[0], atlanan
    s, dusen = an.serit([("%1,0", "a"), ("%2,0", "b" * 800), ("%3,0", "c")], "", 700)
    assert s == "Kilit ölçümler: %1,0 — a; %3,0 — c" and dusen == ["%2,0 — " + "b" * 800], (s, dusen)
    assert "…" not in s, "uzun etiket kırpıldı"
    assert an.serit([("%1,0", "a")], "", 700)[0] == "Kilit ölçüm: %1,0 — a", "tek kalem tekil yazılmadı"
    assert an.serit([("%37,0", "politika faizi")], metin, 700)[0] == "", "boş şerit basıldı"
    # Boş şerit gönderide hiç görünmez ve kapıdan 0 ENGEL geçer.
    sahte = {"tez": "Merkez %9,99 ve fark +0,1 puan. " + "Ölçüm aynı kaynaktan ve aynı günden geliyor. " * 3,
             "satirlar": [("Gelir mi", "Evet, %9,99. Örneklem 31 ay ve kıyas noktası aynı.")],
             "rakamlar": [("%9,99", "merkez")]}
    eski = an.yonetici_ozeti
    an.yonetici_ozeti = lambda _g: sahte
    try:
        t = an.analiz_zinciri({"slug": "sinama-2026-10-05", "govde": "", "title": "5 Ekim 2026 Sınama — şerit",
                               "pubDate": "2026-10-05"})[0]
    finally:
        an.yonetici_ozeti = eski
    assert "Kilit ölçüm" not in t and "Rakamlar" not in t, f"boş şerit basıldı: {t}"
    e, _ = dn.denetle(t, "analiz")
    assert not e, f"şeritsiz analiz gönderisi kapıdan geçmedi: {e}"


def _a8_tez_acilisi():
    """A8: tezin ilk cümlesi bir ölçüm sayısı taşır (analiz/YAZIM.md). Araç
    cümle sırasını değiştirmez; kural gönderi kurulurken UYARI olarak sorulur.
    İlk cümlesi tez payını aşan tez "…" ile kesilmez, düşer ve görünür."""
    import analiz as an
    import uret as ur
    def kur(tez):
        eski = an.yonetici_ozeti
        an.yonetici_ozeti = lambda _g: {"tez": tez, "satirlar": [("Gelir mi", "Evet, %1,5.")], "rakamlar": []}
        an.UYARILAR.clear()
        try:
            t = an.analiz_zinciri({"slug": "sinama-2026-10-05", "govde": "",
                                   "title": "5 Ekim 2026 Sınama — tez", "pubDate": "2026-10-05"})[0]
            return t, list(an.UYARILAR), list(ur.DUSEN)
        finally:
            an.yonetici_ozeti = eski
            an.UYARILAR.clear()
    _, u, _ = kur("Karar sürprizsiz, metin ise tek yönlü değil. Politika faizi %37,0'de sabit.")
    assert any("ilk cümlesi ölçüm sayısı taşımıyor" in x for x in u), f"sayısız tez açılışı uyarı vermedi: {u}"
    _, u, _ = kur("Politika faizi %37,0'de sabit; metin tek yönlü değil.")
    assert not u, f"ölçüm taşıyan tez açılışı uyarı aldı: {u}"
    t, _, d = kur("Uzun " * 200 + "cümle %1,0. İkinci cümle.")
    assert "…" not in t and "Uzun Uzun" not in t, "payı aşan tez kesildi"
    assert any(b == "analiz-bütçe" and "tez" in c for b, c in d), f"düşen tez görünmüyor: {d}"
    # İlk cümlesi satır payını aşan satır da kesilmez: bütünüyle düşer, görünür.
    eski = an.yonetici_ozeti
    an.yonetici_ozeti = lambda _g: {"tez": "Politika faizi %37,0'de sabit. " * 4,
                                    "satirlar": [("Gelir mi", "Evet " * 120 + "%1,5."), ("Ne zaman", "Ekimde, %2,0.")],
                                    "rakamlar": []}
    try:
        t = an.analiz_zinciri({"slug": "sinama-2026-10-05", "govde": "",
                               "title": "5 Ekim 2026 Sınama — satır", "pubDate": "2026-10-05"})[0]
        d = list(ur.DUSEN)
    finally:
        an.yonetici_ozeti = eski
        an.UYARILAR.clear()
    assert "…" not in t and "Gelir mi" not in t and "Ne zaman? Ekimde, %2,0." in t, f"payı aşan satır kesildi: {t}"
    assert any(b == "analiz-bütçe" and c.startswith("Gelir mi") for b, c in d), f"düşen satır görünmüyor: {d}"


def _a8_atif_sozcuk_siniri():
    """Sayfa mobilyası izi sözcük başında aranır (uret.SOL_SINIR): "kapasitede"
    içindeki "sitede" bir atıf değildir; "sitede" ve "yukarıdaki grafikte" atıftır."""
    import analiz as an
    m = an._site_disi("Kapasitede kullanım %77,1. Ayrıntısı sitede duruyor. Grafikte görülür.")
    assert m == "Kapasitede kullanım %77,1.", m


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
    # etiket sökümü noktalamanın önüne boşluk bırakmaz (14.09: "<b>28,2 bp</b>, 10" → "28,2 bp , 10")
    _d = ur._duz("5 yılda <b>28,2 bp</b>, 10 yılda (<em>yıllık</em>) <strong>%</strong> 1,5.")
    assert _d == "5 yılda 28,2 bp, 10 yılda (yıllık) %1,5.", _d
    assert not any("noktalamadan" in x for x in dn.denetle(temiz.replace("Brent", ur._duz("Brent <b>+2,1 bp</b>,")), "bulten")[1])
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
                      .replace("\n\nÖlçüm ve yorumdur", "\n\nGündem: fonlama %37,00 ve büyüme %2,80 açıklandı."
                               "\n\nÖlçüm ve yorumdur"), "bulten")
    assert any("aynı sayıları" in x for x in u), f"ortak sayı uyarısı yok: {u}"
    assert dn.EN_COK == __import__("uret").TEK_TAVAN, "tavan tek kaynak değil"
    import uret as ur
    assert not ur._site_izi_var("TCMB haftalık bülteninde menkul kıymet stoku arttı."), "gerçek bilgi düştü"
    assert ur._site_izi_var("Bu bültenin cevaplaması gereken soru şu."), "öz-atıf düşmedi"
    assert ur._site_izi_var("Ayrıntı aşağıda açıkça yazılır."), "'aşağıda açıkça' düşmedi"


def _kapanis_notu():
    """Sorumluluk notu her gönderinin SON satırı ve kırpmadan muaf."""
    zb = uret.bulten_zinciri(SAHTE_BULTEN)[0]
    assert zb.endswith(uret.SORUMLULUK_BULTEN), zb[-80:]
    # gövde tavanı aşsa bile not kalır
    sisman = {**SAHTE_BULTEN, "yorum": "<p>Uzun uzun anlatı cümlesi burada. </p>" * 400}
    z = uret.bulten_zinciri(sisman)[0]
    assert len(z) <= uret.TEK_TAVAN and z.endswith(uret.SORUMLULUK_BULTEN), (len(z), z[-60:])
    import denetim as dn
    for z_, tur in ((zb, "bulten"),):
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


def _site_izi_hassasiyeti() -> None:
    """İz sözcük ORTASINDA yakalanmaz, sözcük BAŞINDA yakalanır.

    22.09.2026'da ölçüldü: "sitede" izi "kapasitede" sözcüğünün içinde geçiyor
    ve kapasite kullanım oranını anlatan meşru bir cümle gönderiden sessizce
    düşüyordu. Bir denetimin yanlış pozitifi, kaçırdığı kusur kadar pahalıdır —
    burada bedeli, yazarın cümlesinin okura hiç ulaşmaması. İki yön de sınanır:
    gevşetme gerçek izleri kaçırmamalı.
    """
    temiz = ("kapasitede sınırlı bir toparlanma var",
             "kapasitemiz arttı",
             "üniversitede okudu")
    for c in temiz:
        assert not uret._site_izi_var(c), f"yanlış pozitif: {c!r}"
    dusmeli = ("Bu bültenin okuması şudur", "Bu sayfadaki tabloda görünüyor",
               "Panoda iki satır çelişiyor", "Rejim panosunun iki satırı",
               "Sitede ayrıntısı var", "Sitemiz bunu yazdı",
               "Piyasa fotoğrafında yok", "Ayrıntısı jeopolitik bölümünde",
               "Bültende anlatıldı", "Yukarıdaki tabloda duruyor")
    for c in dusmeli:
        assert uret._site_izi_var(c), f"gerçek iz kaçtı: {c!r}"
    # GÖNDERİM KAPISI da aynı sınırla arar (01.10.2026 inceleme): üretici meşru
    # sayıp gönderiye koyduğu cümleyi kapı ham alt dizeyle ENGEL'liyordu.
    import denetim as _dn
    for c in temiz:
        g = f"Haftaya Bakış — 4 Ekim 2026\nABD rafinerileri %93 {c}.\n\n{uret.SORUMLULUK_BULTEN}"
        e = [x for x in _dn.denetle(g, "bulten")[0] if "atıf" in x]
        assert not e, f"kapı sözcük ortasındaki izi site atfı saydı: {c!r} → {e}"
    g = f"Haftaya Bakış — 4 Ekim 2026\nSitede ayrıntısı var.\n\n{uret.SORUMLULUK_BULTEN}"
    assert any("atıf" in x for x in _dn.denetle(g, "bulten")[0]), "kapı gerçek site atfını kaçırdı"


def _bicim3_govde():
    """Biçim 3 (01.10.2026 incelemesi): olguların TEK evi `ne_oldu` maddeleridir;
    gönderi onlarla açılır. Gövde yalnız okumadan kurulunca TMSF, ÖTV ve PCE
    rakamı gönderide hiç geçmiyordu. Pano farkı sayfanın kuralıyla: kur yüzde,
    oran puan, bugün ilerlemeyen gösterge farksız. Öne çıkanlar maddelerin
    saydığı hareketi yinelemez."""
    b3 = {
        "tarih": "2026-10-01", "haftalik": False, "surum": 3, "gundem_kaynagi": "yazili",
        "manset": "PCE yumuşak geldi, uzun uç yine satıldı",
        "yorum": "<p>Bankacılık endeksindeki kayıp belirsizliği fiyatlıyor. " * 30 + "</p>",
        "ozet": {"ne_oldu": "<ul><li><strong>Bankalar.</strong> BDDK beş kuruluşu TMSF'ye devretti; "
                            "bankacılık endeksi −%4,58.</li>"
                            "<li><strong>ABD.</strong> Çekirdek PCE yıllık %3,0 geldi.</li></ul>"},
        "gundem": {"turkiye": "<p>SPK bir aracı kurumun faaliyetlerini durdurdu.</p>",
                   "takvim": "<p>Bugün 14:30 haftalık para-banka.</p>"},
        "piyasa": {"en_cok_hareket": {"sigma_kip": "gunluk", "gunluk": [
            {"ad": "BIST Bankacılık", "deger": -4.58, "birim": "%"},
            {"ad": "MOVE", "deger": 3.61, "birim": "%"}],
            "sigma": [{"ad": "BIST Bankacılık", "deger": -4.58, "birim": "%", "sigma": -3.1},
                      {"ad": "MOVE", "deger": 3.61, "birim": "%", "sigma": 2.2},
                      {"ad": "Brent", "deger": 1.0, "birim": "%", "sigma": 1.2}]}},
        "gostergeler": [
            {"ad": "USD/TRY", "metin": "49,01", "birim": "", "fark_metin": "+0,02", "fark_birim": "%",
             "bugun_yeni": True, "veri_tarihi": "30.09.2026"},
            {"ad": "TÜFE", "metin": "31,51", "birim": "%", "fark_metin": "−0,24", "bugun_yeni": True,
             "veri_tarihi": "09.2026"},
            {"ad": "Net rezerv", "metin": "55,8", "birim": "mlr USD", "fark_metin": "−6,5",
             "bugun_yeni": False, "veri_tarihi": "18.09.2026"}],
    }
    t = uret.bulten_zinciri(b3)[0]
    assert "TMSF" in t and "%3,0" in t, "maddelerin olguları gönderide yok"
    assert t.index("TMSF") < t.index("belirsizliği fiyatlıyor"), "maddeler okumadan sonra"
    assert "PCE yumuşak geldi" in t.split("\n\n")[0], "manşet başlıkta değil"
    assert "USD/TRY 49,01 (+%0,02; 30 Eyl)" in t, "kur farkı yüzde basılmadı"
    assert "TÜFE %31,51 (−0,24 puan" in t, "oranın farkı puan değil"
    # Pano yalnız BUGÜN YENİ kartı taşır (05.10.2026): ilerlemeyen kart hiç basılmaz.
    assert "Net rezerv" not in t, "ilerlemeyen gösterge panoya girdi"
    ola = next(l for l in t.split("\n") if l.startswith("Olağandışı hareketler"))
    assert "Bankacılık" not in ola, "maddelerin saydığı hareket olağandışı satırında yinelendi"
    assert "MOVE +%3,61 (+2,2σ)" in ola, "maddelerde olmayan σ hareketi düştü"
    assert "Brent" not in ola and "Günün öne çıkanları" not in t, "eşik altı hareket ya da ham liste girdi"
    assert t.count("14:30") == 1, "takvim iki kez girdi"
    yazisiz = uret.bulten_zinciri({**b3, "yorum": ""})[0]
    assert "TMSF" in yazisiz, "okuma yokken maddeler düştü"
    # Kayıt defteri okunurken bulten/ yola girmez: girerse sonraki `import
    # denetim` / `import uret` bültenin aynı adlı modülüne düşer.
    assert str(uret.KOK / "bulten") not in sys.path, "bulten/ sys.path'e girdi"
    # İŞLEM FİKİRLERİ GÖNDERİYE GİRMEZ (karar 04.10.2026): sayfanın kendi
    # bölümüdür ve kendi uyarı metniyle basılır; gönderi bu alanı okumaz.
    # Kilit iki kipte de: haftalıkta "Ana senaryo" satırı gönderiye girdiği
    # için senaryodan türeyen fikir oraya sızmaya en yakın yerdir.
    isaret = "FIKIRISARETI"
    fk = [{"baslik": isaret, "gerekce": isaret, "ne_bozar": isaret, "yapi_metni": isaret,
           "yon_metni": isaret}]
    karne = {"kayitlar": [{"baslik": isaret, "durum": "acik"}], "sayim": {}}
    for kip in (False, True):
        bb = {**b3, "haftalik": kip, "fikirler": fk, "fikir_karne": karne,
              "fikir_kapat": [{"kimlik": "x", "sebep": isaret}]}
        if kip:
            bb["gundem"] = {**bb["gundem"], "risk": "<h3>Ana senaryo</h3><p>Faiz yatay kalır.</p>"}
        metin = "\n".join(uret.bulten_zinciri(bb))
        assert isaret not in metin, f"işlem fikri gönderiye girdi ({'haftalık' if kip else 'günlük'})"


def _haftalik_gonderi_tur2():
    """İkinci inceleme turu (01.10.2026): kırpma sayıyla bitmez · günlük gündem
    satırı bölünmez · gün gün takvim içeriksiz gün başlığıyla bitmez · ana
    senaryo satırı yalnız ilk alt bölümün gövdesidir ve etiketi düşmez."""
    import denetim as _dn
    # (1) Virgülle sıralanan rakam listesi dar satırda (05.10.2026 sözleşmesi):
    #     tek cümle satıra sığmıyorsa BÜTÜNÜYLE düşer — ne yan tümcede ne
    #     sayıda kesilir; satır içeriksiz etiketle de basılmaz.
    liste = ("16 Eylül kapanışında BIST 100 %5,54 düşüşle 13.123, BIST 30 %5,58 düşüşle 15.716, "
             "sanayi endeksi %5,79 düşüşle 18.325, banka endeksi %6,38 düşüşle 15.150 puana indi, "
             "holding endeksi %4,12 düşüşle 9.871 ve hizmetler %3,05 düşüşle 11.204 puanda kapattı")
    assert len(liste) > 190, "fikstür kırpılmıyor: sınama hiçbir şeyi ölçmez"
    for sinir in (190, 150):
        assert uret._kirp(liste, sinir) == "", f"tek cümle {sinir}'de kesildi"
    uzun = liste + ", " + liste + "."
    assert len(uzun) > uret.SATIR_ESNEK
    gg = {"tarih": "2026-10-02", "haftalik": False, "surum": 3, "gundem_kaynagi": "yazili",
          "ozet": {"ne_oldu": "<ul><li>Madde bir.</li></ul>"},
          "gundem": {"turkiye": f"<p>{uzun}</p>", "kuresel": f"<p>{liste}.</p>"}}
    t1 = uret.bulten_zinciri(gg)[0]
    assert "\nTürkiye:" not in t1 and any(b == "turkiye" for b, _ in uret.DUSEN), \
        "esnek sınırı aşan tek cümleli satır düşmedi ya da düşüşü görünmez"
    assert f"Küresel: {liste}." in t1, "esnek sınıra sığan tek cümle (etiketli satır) düştü"
    assert not _dn.BOS_ETIKET.findall(t1) and "…" not in t1, t1
    # (2) Günlük gündem satırı bölünmez (her etiketli bölüm 260'a kadar).
    # Üç cümle 3·84+2 ≈ 254 karakter: 260'lık satıra sığar, 246'lıkta düşerdi.
    cum = ["Kısa uç gevşedi ve uzun uç ABD getirileriyle birlikte çok {} yükseldi bugün sabah.",
           "Kur sakin kaldı ve taşıma makası çok {} genişledi, fonlama ise tavanda durdu yine.",
           "Hisse tarafında bankalar çok {} geriledi, sanayi endeksi ise yatay kapattı seansı."]
    def uzun(r):
        return "<p>" + " ".join(c.format(r) for c in cum * 2) + "</p>"
    gb = {"tarih": "2026-10-02", "haftalik": False, "surum": 3, "gundem_kaynagi": "yazili",
          "ozet": {"ne_oldu": "<ul><li>Madde bir.</li></ul>"},
          "gundem": {"turkiye": uzun("hızla"), "kuresel": uzun("sert"), "emtia": uzun("ağır")}}
    t = uret.bulten_zinciri(gb)[0]
    sat = [l for l in t.split("\n") if l.startswith(("Türkiye:", "Küresel:", "Emtia:"))]
    assert len(sat) == 3 and min(l.count(". ") + 1 for l in sat) == 3, \
        f"günlük gündem satırı haftalık bütçeyle bölündü: {[len(l) for l in sat]}"
    # Sıra sayısındaki nokta cümle sonu değildir.
    k = uret._kirp("Piyasa bugün sakin kaldı ve kısa uç 3. gün de yatay seyretti, fonlama tavanda "
                   "durdu. " * 4, 150)
    assert not re.search(r"\d\.$", k), f"kırpma sıra sayısında kesti: {k!r}"
    # (3) Gün gün takvim: sondaki içeriksiz gün başlığı düşer.
    hb = {"tarih": "2026-10-04", "haftalik": True, "surum": 3, "gundem_kaynagi": "yazili",
          "ozet": {"ne_oldu": "<ul><li>Madde bir.</li></ul>"},
          "gundem": {"takvim": "<p><strong>Pazartesi 5 Ekim.</strong> TÜİK eylül TÜFE'sini yayımlıyor. "
                               "Çekirdek hız fiyatlamayı belirler.</p><p><strong>Salı 6 Ekim.</strong> "
                               + "Uzun bir cümle " * 60 + ".</p>",
                     "risk": "<h3>Ana senaryo: kısa uç gevşer</h3><p>Bu senaryoda TÜFE aylık %1,5'in "
                             "altında gelir ve kısa uç gevşer.</p><h3>Alternatif: kur baskısı</h3>"
                             "<p>Kur haftalık %0,5'i aşarsa fonlama tavana çıkar.</p>"}}
    t = uret.bulten_zinciri(hb)[0]
    ileri = next(p for p in t.split("\n\n") if p.startswith("Önümüzdeki hafta"))
    assert not ileri.rstrip().endswith("Salı 6 Ekim."), f"takvim içeriksiz gün başlığıyla bitti: {ileri[-60:]!r}"
    assert "Pazartesi 5 Ekim: TÜİK eylül TÜFE'sini yayımlıyor." in ileri, "baştaki gün satırı düştü"
    # (4) Ana senaryo: etiket "Bu senaryoda …" açılışında düşmez, alternatif girmez.
    ana = next(l for l in t.split("\n") if "senaryo" in l.lower() and "TÜFE aylık" in l)
    assert ana.startswith("Ana senaryo:"), f"ana senaryo etiketi düştü: {ana!r}"
    # Haftalık iskelet (05.10.2026): alternatif KENDİ satırında girer, ana
    # senaryonun satırına karışmaz.
    assert "fonlama tavana" not in ana, "alternatif patika ana senaryo satırına girdi"
    assert "\nAlternatif: kur baskısı. " not in t and "\nAlternatif: Kur haftalık %0,5'i aşarsa fonlama tavana çıkar." in t, \
        "alternatif senaryo kendi satırında yok"


# ── 05.10.2026 gönderi önerileri (U1 · U2 · U3 · U4 · U6 · U7 · U10) ──────────

def _gunluk_fikstur(**ek) -> dict:
    """Biçim 3 günlük sayının gerçek biçimini taşıyan fikstür (05.10'dan)."""
    b = {
        "tarih": "2026-10-05", "haftalik": False, "surum": 3, "gundem_kaynagi": "yazili",
        "manset": "Euro dibe indi, TL eğrisi TÜFE'yi bekliyor: aylık beklenti %2,18",
        "ozet": {"ne_oldu": "<ul>"
                 "<li><strong>TÜFE günü.</strong> TÜİK eylül TÜFE'sini bugün yayımlıyor; beklenti %2,18.</li>"
                 "<li><strong>Kur.</strong> Dolar/TL %0,23 (2,9σ) artışla 49,14'te kapandı.</li>"
                 "<li><strong>Hong Kong.</strong> Hang Seng %2,6 (−2,7σ) düştü.</li>"
                 "<li><strong>Euro bu sabah.</strong> Euro Asya seansında %0,8 geriledi.</li></ul>"},
        "yorum": ("<p>TL tahvili enflasyonu veriden önce okudu; kur aynı rahatlığı paylaşmadı.</p>"
                  "<p><strong>Mekanizma.</strong> Kısa ucu iki şey taşıdı. Fed artırımı fiyatlamadan silindi.</p>"),
        "gundem": {
            "turkiye": "<p><strong>TL faizi ve DİBS.</strong> 2 yıllık spot getiri %40,15, 7 yıllık %33,55.</p>",
            "kuresel": "<p><strong>Euro ve Avrupa siyaseti.</strong> Euro dört haftalık düşüş serisini derinleştirdi.</p>",
            "emtia": "<p><strong>Ürün ve ham petrol.</strong> Euro dışında distilat marjı 4,2 dolar daraldı.</p>",
            "takvim": "<p><strong>Bugün 10:00 · TÜFE ve Yİ-ÜFE (Eylül).</strong> Ağustos'ta aylık TÜFE %1,84'tü. "
                      "Aylık TÜFE %2,5'i aşarsa kısa uç yükselir.</p>"
                      "<p><strong>Salı ve sonrası.</strong> Hazine 8 yıllık tahvil satıyor.</p>",
            "risk": "<ul><li><strong>Yüksek aylık TÜFE</strong> → kısa uç; izlenecek: 2 yıllık getirinin %40,5'in üstüne dönmesi.</li>"
                    "<li><strong>Kuzey Denizi grevi</strong> → Brent ve ürün marjı; izlenecek: Forties üretim kesintisi.</li></ul>"},
        "piyasa": {"en_cok_hareket": {"sigma_kip": "gunluk", "sigma": []}, "gruplar": []},
        "gostergeler": [],
    }
    b.update(ek)
    return b


def _u1_tam_birim():
    """U1: "…" üretilmez; seçim birimi madde, TAM cümle ya da satırdır.

    Cümle sınırı rakamla biten ve rakamla başlayan cümleyi de tanır (01.10
    Küresel satırı "%5,089. Aynı" ve "açıldı. 5, 10" sınırlarını göremediği için
    kelime ortasından kesiliyordu); sıra sayısını sağdaki küçük harf ayırır;
    dengesiz parantez içindeki nokta sınır değildir ("GSYH (II. Çeyrek)")."""
    c = uret.cumleler("10 yıllık %5,293, 5 yıllık %5,089. Aynı gün dolar yükseldi.")
    assert c == ["10 yıllık %5,293, 5 yıllık %5,089.", "Aynı gün dolar yükseldi."], c
    c = uret.cumleler("Eğri uzun uçtan açıldı. 5, 10 ve 30 yıllık yükseldi.")
    assert len(c) == 2 and c[1].startswith("5, 10"), c
    c = uret.cumleler("Perşembe 38. haftanın verisi geliyor. Sonra rezerv.")
    assert c[0] == "Perşembe 38. haftanın verisi geliyor.", c
    c = uret.cumleler("GSYH (II. Çeyrek) beklentiyi aştı. Kur sakin kaldı.")
    assert c[0] == "GSYH (II. Çeyrek) beklentiyi aştı.", f"parantez içinde kesildi: {c}"
    assert uret._kirp("10 yıllık %5,293, 5 yıllık %5,089. Aynı gün dolar yükseldi.", 40) \
        == "10 yıllık %5,293, 5 yıllık %5,089.", "rakamla biten cümle sınır sayılmadı"
    for metin, sinir in (("Uzun tek bir cümle " * 30 + ".", 120), ("Banka eylülde %1,25 ve", 20),
                         ("GSYH (II. Çeyrek) beklentiyi aştı ve kur sakin kaldı.", 25)):
        k = uret._kirp(metin, sinir)
        assert k == "" and "…" not in k, f"sığmayan birim kesildi: {k!r}"
    # Satır sayısızsa bir sonraki cümle de alınır; etiketli satır 330'a esner.
    assert uret._satir_sec("Eğrinin biçimi. Kısa uç %37,64'e çıktı. Uzun uç sakin.", 20, esnek=uret.SATIR_ESNEK) \
        == "Eğrinin biçimi. Kısa uç %37,64'e çıktı.", "sayısız ilk cümlenin ardı alınmadı"
    # Tavanı zorlayan sayı: ölçü kırpılmamış gövdeden; `_kapat` kesmez, "…" yok.
    sisman = _gunluk_fikstur(yorum="<p>" + "Uzun uzun anlatı cümlesi %1,5 burada. " * 300 + "</p>")
    sisman["ozet"]["ne_oldu"] = "<ul>" + ("<li>Madde cümlesi %2,1 burada duruyor ve uzundur. " * 6 + "</li>") * 6 + "</ul>"
    t = uret.bulten_zinciri(sisman)[0]
    assert len(t) <= uret.TEK_TAVAN and "…" not in t, (len(t), t[-80:])
    assert not [d for d in uret.DUSEN if d[0] == "tavan"], "gövde `_kapat`ta sondan kırpıldı"
    import denetim as dn
    assert not dn.denetle(t, "bulten")[0], dn.denetle(t, "bulten")[0]
    # `_kapat` son çare kesimi de TAM cümlede yapar: "…" yok, not sonda.
    k = uret._kapat("Uzun cümle %1,5 burada duruyor ve sürüyor. " * 200, uret.SORUMLULUK_BULTEN)
    assert "…" not in k and len(k) <= uret.TEK_TAVAN and k.endswith(uret.SORUMLULUK_BULTEN), (len(k), k[-60:])
    assert k[:-len(uret.SORUMLULUK_BULTEN)].rstrip().endswith("sürüyor."), "gövde cümle sınırında bitmiyor"


def _u2_ilk280():
    """U2: günün sınavı ilk ekranda. Takvimin ilk "Bugün…" paragrafı
    KOPYALANMAZ, TAŞINIR: maddelerin hemen arkasında durur ve "Beklenen:"den
    çıkar. Haftalıkta taşınmaz."""
    t = uret.bulten_zinciri(_gunluk_fikstur())[0]
    paragraflar = t.split("\n\n")
    assert paragraflar[1].startswith("· TÜFE günü."), paragraflar[1][:40]
    assert paragraflar[2].startswith("Bugün 10:00 · TÜFE ve Yİ-ÜFE (Eylül). Ağustos'ta"), \
        f"günün sınavı maddelerin ardında değil: {paragraflar[2][:60]!r}"
    assert t.count("Bugün 10:00") == 1 and t.count("%1,84") == 1, "takvim paragrafı iki evde"
    bek = next(p for p in paragraflar if p.startswith("Beklenen:"))
    assert bek.startswith("Beklenen: Salı ve sonrası. Hazine 8 yıllık"), bek
    hb = _gunluk_fikstur(haftalik=True)
    hb["gundem"]["takvim"] = ("<p><strong>Bugün 10:00 · TÜFE.</strong> Pazartesi %2,1 bekleniyor.</p>"
                              "<p><strong>Salı 6 Ekim.</strong> Hazine 4 yıllık ihale yapıyor.</p>")
    th = uret.bulten_zinciri(hb)[0]
    assert not th.split("\n\n")[2].startswith("Bugün"), "haftalıkta 'Bugün' paragrafı maddelerin ardına taşındı"
    assert "\nÖnümüzdeki hafta\nBugün 10:00 · TÜFE: Pazartesi %2,1 bekleniyor." in th, \
        "haftalık takvimde gün satırı yok"


def _u3_pano_ve_olagandisi():
    """U3: Pano yalnız BUGÜN YENİ karttan, değeri gövdede geçmeyenden; kur
    "İstanbul 18:00" tanımını yalnız saatlik kapanışta taşır. Olağandışı satırı
    sayfanın σ listesinden, eşikle, satırın KENDİ seans tarihiyle; pazartesi
    sayısı cuma seansını "Günün" diye basmaz."""
    kur = {"ad": "USD/TRY", "metin": "49,14", "birim": "", "fark_metin": "+0,27", "fark_birim": "%",
           "bugun_yeni": True, "veri_tarihi": "02.10.2026", "kapanis_tanimi": "İstanbul 18:00", "anahtar": "kur"}
    kartlar = [
        dict(kur, metin="49,20"),
        {"ad": "Net rezerv", "metin": "53,4", "birim": "mlr USD", "fark_metin": "−2,4",
         "bugun_yeni": False, "veri_tarihi": "25.09.2026", "anahtar": "h_net"},
        {"ad": "TLREF", "metin": "36,84", "birim": "%", "fark_metin": "+0,02",
         "bugun_yeni": True, "veri_tarihi": "02.10.2026", "anahtar": "tlref"},
        {"ad": "DİBS gösterge getirisi (2 yıl)", "metin": "40,00", "birim": "%", "fark_metin": "−0,16",
         "bugun_yeni": True, "veri_tarihi": "02.10.2026", "anahtar": "gosterge_ytm"},
        {"ad": "Swap hariç net rezerv", "metin": "39,9", "birim": "mlr USD", "fark_metin": "−3,2",
         "bugun_yeni": True, "veri_tarihi": "25.09.2026", "anahtar": "h_swap_haric"}]
    satir = {"ad": "USD/TRY", "tarih": "2026-10-02", "kapanis_tanimi": "İstanbul 18:00",
             "kapanis_ani": "2026-10-02T15:00:00Z"}
    piy = {"en_cok_hareket": {"sigma_kip": "gunluk", "sigma": [
        {"ad": "USD/TRY", "deger": 0.23, "birim": "%", "sigma": 2.9},
        {"ad": "Hang Seng", "deger": -2.6, "birim": "%", "sigma": -2.7},
        {"ad": "ABD 10 yıllık", "deger": 7.2, "birim": "bp", "sigma": 2.5},
        {"ad": "Gümüş", "deger": -1.9, "birim": "%", "sigma": -1.9}]},
        "gruplar": [{"satirlar": [satir, {"ad": "ABD 10 yıllık", "tarih": "2026-10-02"},
                                  {"ad": "Hang Seng", "tarih": "2026-10-02"}]}]}
    t = uret.bulten_zinciri(_gunluk_fikstur(gostergeler=kartlar, piyasa=piy))[0]
    pano = next(l for l in t.split("\n") if l.startswith("Pano: "))
    assert pano == ("Pano: USD/TRY 49,20 (+%0,27; 2 Eki, İstanbul 18:00) · TLREF %36,84 (+0,02 puan; 2 Eki) · "
                    "Swap hariç net rezerv 39,9 mlr USD (−3,2; 25 Eyl)"), pano
    assert "Net rezerv 53,4" not in t, "ilerlemeyen kart girdi"
    # Değeri gövdede zaten geçen kart yinelenmez (maddede "49,14").
    t2 = uret.bulten_zinciri(_gunluk_fikstur(gostergeler=[kur], piyasa=piy))[0]
    assert "Pano:" not in t2, "değeri gövdede geçen kart panoda yinelendi"
    assert "DİBS gösterge" not in pano, "gövde 2 yıllık getiri anarken ikinci bir 2 yıllık tanım basıldı"
    ola = next(l for l in t.split("\n") if l.startswith("Olağandışı"))
    assert ola == "Olağandışı hareketler (2 Eki cuma): ABD 10 yıllık +7,2 bp (+2,5σ)", ola
    assert "Günün" not in t, "pazartesi sayısı cuma seansını 'Günün' diye bastı"
    # Yedek tanım (günlük bar) okura basılmaz.
    satir.update(kapanis_ani=None, kapanis_tanimi="Londra gece yarısı (günlük bar; saatlik bar alınamadı)")
    t = uret.bulten_zinciri(_gunluk_fikstur(gostergeler=kartlar, piyasa=piy))[0]
    assert "İstanbul 18:00" not in t and "Londra" not in t, "yedek kapanış tanımı basıldı"
    # Karma seans: gün satır başına.
    piy["en_cok_hareket"]["sigma"].append({"ad": "Bitcoin", "deger": 4.1, "birim": "%", "sigma": 2.3})
    piy["gruplar"][0]["satirlar"].append({"ad": "Bitcoin", "tarih": "2026-10-04"})
    t = uret.bulten_zinciri(_gunluk_fikstur(gostergeler=kartlar, piyasa=piy))[0]
    ola = next(l for l in t.split("\n") if l.startswith("Olağandışı"))
    assert ola.startswith("Olağandışı hareketler: ") and "(+2,5σ; 2 Eki cuma)" in ola \
        and "(+2,3σ; 4 Eki pazar)" in ola, ola
    # Boş pano basılmaz.
    t = uret.bulten_zinciri(_gunluk_fikstur(gostergeler=[kartlar[1]]))[0]
    assert "Pano:" not in t, "boş pano satırı basıldı"
    # Haftalık: "Seviyeler", oranın farkı puan.
    hb = _gunluk_fikstur(haftalik=True, gostergeler=kartlar)
    th = uret.bulten_zinciri(hb)[0]
    sev = next(l for l in th.split("\n") if l.startswith("Seviyeler: "))
    assert "TLREF %36,84 (+0,02 puan; 2 Eki)" in sev and "Pano:" not in th, sev


def _u4_maddeler_oncelikli():
    """U4: maddeler bütçede ÖNCELİKLİ — taşınca önce olağandışı, sonra pano,
    sonra gündem düşer; "Beklenen" korunur. Maddelerle aynı konuyu yineleyen ve
    yeni sayı taşımayan gündem satırı düşer, sayılı satır kalır. Okumanın kalın
    ara başlığı cümleye yapışmaz."""
    b = _gunluk_fikstur()
    t = uret.bulten_zinciri(b)[0]
    assert "\nKüresel:" not in t and any("aynı konu" in d[1] for d in uret.DUSEN if d[0] == "kuresel"), \
        "maddeyi yineleyen sayısız gündem satırı düşmedi"
    assert "\nEmtia: Ürün ve ham petrol. Euro dışında distilat marjı 4,2 dolar daraldı." in t, \
        "maddede olmayan sayıyı (4,2) taşıyan satır düştü"
    assert "Mekanizma: Kısa ucu iki şey taşıdı." in t and "Mekanizma. Kısa" not in t, \
        "okumanın kalın ara başlığı cümleye yapıştı"
    # Taşma: altı uzun madde, dolu gündem, uzun "Bugün", dolu pano ve σ satırı.
    m = "Madde cümlesi %2,1 burada uzun uzun anlatılıyor ve devam ediyor, bitmiyor. "
    b["ozet"]["ne_oldu"] = "<ul>" + "".join(f"<li><strong>Konu {i}.</strong> {m * 5}</li>" for i in range(6)) + "</ul>"
    b["gundem"]["takvim"] = ("<p><strong>Bugün 10:00 · TÜFE.</strong> " + "Takvim cümlesi %1,84 ile uzun. " * 20 + "</p>"
                             "<p><strong>Salı ve sonrası.</strong> Hazine 8 yıllık tahvil satıyor.</p>")
    for k in ("turkiye", "kuresel", "emtia"):
        b["gundem"][k] = "<p>" + f"{k} satırı %4,4 ölçümünü yazıyor ve uzun. " * 7 + "</p>"
    b["gostergeler"] = [{"ad": f"Kart {i}", "metin": f"{i},7{i}", "birim": "%", "fark_metin": "+0,10",
                         "bugun_yeni": True, "veri_tarihi": "02.10.2026"} for i in range(1, 7)]
    b["piyasa"]["en_cok_hareket"]["sigma"] = [{"ad": f"Seri {i}", "deger": 3.1, "birim": "%", "sigma": 3.0}
                                              for i in range(6)]
    b["yorum"] = "<p>" + "Okuma cümlesi %3,3 ile kuruldu. " * 14 + "</p>"
    t = uret.bulten_zinciri(b)[0]
    assert len(t) <= uret.TEK_TAVAN
    assert sum(1 for l in t.split("\n") if l.startswith("· Konu")) == 6, "madde düştü — maddeler öncelikli değil"
    dusen = [d[0] for d in uret.DUSEN if d[1].startswith("bütçe: ")]
    assert dusen and dusen[0] == "olagandisi", f"taşmada ilk düşen olağandışı satırı değil: {dusen[:4]}"
    # Sıra TAM sorulur (05.10.2026 incelemesi): eski ölçüt pano hiç düşmeyince
    # `else 99` dalına düşüp geçiyordu ve pano önceliği gündemin üstüne çıkınca
    # sıra bozulduğu hâlde yeşil kalıyordu.
    assert "pano" in dusen and "gundem" in dusen, f"fikstür pano ve gündemi düşürmüyor: {dusen}"
    son_ola = max(i for i, d in enumerate(dusen) if d == "olagandisi")
    son_pano = max(i for i, d in enumerate(dusen) if d == "pano")
    assert son_ola < dusen.index("pano") and son_pano < dusen.index("gundem"), \
        f"düşme sırası olağandışı < pano < gündem değil: {dusen}"
    assert "Beklenen: Salı ve sonrası. Hazine 8 yıllık tahvil satıyor." in t, "Beklenen kırpıldı"
    assert not [d for d in uret.DUSEN if d[0] == "tavan"]


def _haftalik_fikstur(**ek) -> dict:
    b = {"tarih": "2026-10-04", "haftalik": True, "surum": 3, "gundem_kaynagi": "yazili",
         "manset": "İç şok rezervle emildi: BIST 100 haftada −%4,88",
         "ozet": {"ne_oldu": "<ul>" + "".join(
             f"<li><strong>Konu {i}.</strong> " + "Haftanın olgusu %1,{0} ile ölçüldü ve anlatıldı. ".format(i) * 5
             + "</li>" for i in range(10)) + "</ul>"},
         "yorum": "<p>Haftanın okuması uzun.</p>",
         "izleme": {"karne": {"notlanan": 39, "tuttu": 19, "kismen": 15, "tutmadi": 5}},
         "fikir_karne": {"kayitlar": [{"baslik": "FIKIRISARETI", "durum": "acik"}]},
         "fikirler": [{"baslik": "FIKIRISARETI", "giris": 0.044021, "hedef": 0.0392, "stop": 0.048, "ondalik": 4}],
         "gundem": {
             "risk": "<h3>Ana senaryo: TÜFE beklenti civarında gelir</h3><p>Eylül enflasyonu beklenti "
                     "aralığında gelirse TL eğrisi kısa uçtan gevşemeyi sürdürür.</p>"
                     "<h3>Alternatif: enflasyon yukarı şaşırtır</h3><p><strong>Tetik.</strong> Aylık TÜFE "
                     "%2,6'yı aşar.</p><h3>Kuyruk: rezerv aşınması kur ritmini bozar</h3><p><strong>Tetik."
                     "</strong> Distilat oranı 0,0480'in üstüne çıkar.</p>",
             "takvim": "".join(f"<p><strong>{g}.</strong> Haftanın ağırlığı burada. TÜİK 10:00'da veri "
                               f"yayımlıyor; önceki %1,84, güçlü gelirse kısa uç yükselir, zayıf gelirse "
                               f"indirim fiyatlaması güçlenir ve eğri dikleşir. " + "Ek cümle uzun. " * 10 + "</p>"
                               for g in ("Pazartesi 5 Ekim", "Salı 6 Ekim", "Çarşamba 7 Ekim",
                                         "Perşembe 8 Ekim", "Cuma 9 Ekim")),
             "karne": "<p>Giriş paragrafı.</p><p><strong>Kredi ile hisse oynaklığı.</strong> Çağrı (16.09 "
                      "notu) tutmadı. İkinci cümle.</p><p><strong>Önümüzdeki hafta sınanacaklar.</strong> "
                      "Üç çağrı pazartesi sınanacak.</p><p><strong>Açık ana senaryo.</strong> 16 Ekim'de.</p>",
             "turkiye": "<p><strong>Eğri.</strong> Kısa uç %37,64.</p>",
             "kuresel": "<p><strong>ABD.</strong> İstihdam 29 bin.</p>"},
         "piyasa": {"en_cok_hareket": {"sigma_kip": "haftalik", "haftalik": [
             {"ad": "BIST Sınai", "deger": -7.76, "birim": "%"}],
             "sigma": [{"ad": "USD/TRY", "deger": 0.37, "birim": "%", "sigma": 14.9}]}},
         "gostergeler": [{"ad": f"Kart {i}", "metin": f"{i},7{i}", "birim": "%", "fark_metin": "+0,10",
                          "bugun_yeni": True, "veri_tarihi": "02.10.2026"} for i in range(1, 7)]}
    b.update(ek)
    return b


def _u6_haftalik_iskelet():
    """U6: haftalık iskelet 3.800 içinde — maddeler (dinamik pay) → Senaryolar
    (ana · alternatif · kuyruk) → Önümüzdeki hafta gün gün → Karne → Seviyeler.
    Konu satırları, okuma ve öne çıkanlar ÇIKAR. Taşınca önce maddeler sondan
    düşer; takvimin ilk günü, karnenin sayımı ve ana senaryo düşmez; kuyruk
    satırı tetiksiz kalmaz; işlem fikri ve fikir seviyesi girmez."""
    t = uret.bulten_zinciri(_haftalik_fikstur())[0]
    assert len(t) <= uret.TEK_TAVAN and "…" not in t, len(t)
    assert not [d for d in uret.DUSEN if d[0] == "tavan"], "haftalık gövde `_kapat`ta kırpıldı"
    # Taşınca İLK düşen Seviyeler'dir (05.10.2026, kullanıcı kararı); maddeler ondan sonra.
    butce = [d[0] for d in uret.DUSEN if d[1].startswith("bütçe: ")]
    assert butce and butce[0] == "pano", f"taşmada ilk düşen Seviyeler değil: {butce[:4]}"
    # Dinamik pay: maddeler uzayınca dördüncü ve sonrakiler düşer, ama ancak
    # Seviyeler tümüyle düştükten SONRA; ilk üç madde kalır.
    uzun = _haftalik_fikstur()
    uzun["ozet"] = {"ne_oldu": "<ul>" + "".join(
        f"<li><strong>Konu {i}.</strong> " + "Haftanın olgusu %1,{0} ile ölçüldü ve anlatıldı. ".format(i) * 5
        + "</li>" for i in range(16)) + "</ul>"}   # madde sayısı artar (madde başına pay 250)
    uret.DUSEN.clear()
    t2 = uret.bulten_zinciri(uzun)[0]
    butce2 = [d[0] for d in uret.DUSEN if d[1].startswith("bütçe: ")]
    assert "ne_oldu" in butce2, "fikstür tavanı aşmıyor: dinamik pay sınanmadı"
    assert "pano" not in butce2[butce2.index("ne_oldu"):] and "Seviyeler:" not in t2, \
        f"madde düşerken Seviyeler hâlâ duruyordu: {butce2}"
    assert all(f"· Konu {i}." in t2 for i in range(3)), "ilk üç madde düştü"
    assert "\nSenaryolar\nAna senaryo: Eylül enflasyonu beklenti aralığında gelirse" in t
    assert "\nAlternatif: enflasyon yukarı şaşırtır. Tetik: Aylık TÜFE %2,6'yı aşar." in t, \
        "alternatif satırı tetiğini taşımıyor"
    assert "Kuyruk:" not in t and any("işlem fikri seviyesi" in d[1] for d in uret.DUSEN), \
        "açık fikrin seviyesini (0,0480) taşıyan senaryo satırı gönderiye girdi"
    assert ("\nÖnümüzdeki hafta\nPazartesi 5 Ekim: Haftanın ağırlığı burada. TÜİK 10:00'da veri yayımlıyor; "
            "önceki %1,84, güçlü gelirse kısa uç yükselir, zayıf gelirse indirim fiyatlaması güçlenir ve eğri dikleşir.") in t, \
        "takvimin ilk günü ya da 'sayısız ilk cümle → bir sonraki' kuralı yok"
    assert "\nKarne — şimdiye kadar notlanan 39: tuttu 19 · kısmen 15 · tutmadı 5\nKredi ile hisse oynaklığı: Çağrı (16.09 notu) tutmadı." in t
    assert "sınanacak" not in t and "16 Ekim'de" not in t, "karneye takvim/açık senaryo paragrafı girdi"
    for x in ("\nTürkiye:", "\nKüresel:", "Haftanın öne çıkanları", "olağandışı", "okuması uzun",
              "FIKIRISARETI", "Gündem\n"):
        assert x not in t, f"haftalıkta çıkması gereken parça var: {x!r}"
    # Fikir seviyesi yokken kuyruk satırı TETİĞİYLE girer (tetiksiz kalmaz).
    t = uret.bulten_zinciri(_haftalik_fikstur(fikirler=[]))[0]
    assert "\nKuyruk: rezerv aşınması kur ritmini bozar. Tetik: Distilat oranı 0,0480'in üstüne çıkar." in t, \
        "kuyruk satırı tetiksiz kaldı"
    # Ana senaryo düşmez: ilk cümlesi 330'u da aşarsa yazarın alt başlığı yazılır.
    hb = _haftalik_fikstur()
    hb["gundem"]["risk"] = "<h3>Ana senaryo: kısa uç gevşer</h3><p>" + "Çok uzun bir ana senaryo cümlesi " * 15 + ".</p>"
    t = uret.bulten_zinciri(hb)[0]
    assert "\nSenaryolar\nAna senaryo: kısa uç gevşer." in t, "ana senaryo satırı düştü"
    # Ana senaryonun önceliği None (düşmez) — tavan her şeyi düşürse de kalır.
    assert [o for _, o in uret._senaryolar(_haftalik_fikstur(fikirler=[]))][0] is None, \
        "ana senaryo düşebilir bir öncelik taşıyor"
    sisman = _haftalik_fikstur(fikirler=[], manset="Manşet %1,5 ölçümü taşıyor. " * 62)
    t = uret.bulten_zinciri(sisman)[0]
    assert "\nSenaryolar\nAna senaryo:" in t, "tavan aşımında ana senaryo düştü"


def _u7_kaynak_ve_cekince():
    """U7: gündem satırında kaynağı adıyla anan cümle bütçe içinde önceliklidir;
    "sebebi netleşmedi" okumanın kesiminin HEMEN ardındaysa öncülüyle birlikte
    girer (bitişik uzatma), uzaktaysa girmez — cümle seçilmez."""
    dolgu = "Bu dolgu cümlesi yeterince uzun ve bir şey söylemiyor. "
    b = _gunluk_fikstur()
    b["gundem"]["turkiye"] = ("<p><strong>TL faizi.</strong> 2 yıllık %40,15'e indi. " + dolgu * 4
                              + "Bloomberg HT'ye göre baskı küresel getiriden geliyor.</p>")
    t = uret.bulten_zinciri(b)[0]
    tr = next(l for l in t.split("\n") if l.startswith("Türkiye:"))
    # Bitişik seçim kaynak cümlesine ULAŞAMAZ (dört dolgu 260'ı doldurur);
    # öncelik onu alır ve bir dolgu cümlesini dışarıda bırakır.
    assert "Bloomberg HT'ye göre" in tr and tr.count("Bu dolgu") < 4 \
        and len(tr) <= uret.GUNDEM_PARCA + len("Türkiye: "), tr
    assert uret._kaynakli("Reuters'a göre faiz arttı.") and not uret._kaynakli("Ağustos'a göre arttı.")
    temel = "<p>" + "Okuma cümlesi %1 kuruldu. " * 12 + "</p>"
    yakin = temel + "<p>Kurun cumaki hızlanması eşlik etmedi. Sebebi netleşmedi; artış küçük. Son cümle.</p>"
    t_, ek = uret._okuma_sec(yakin, 330)
    assert ek and ek[-1].startswith("Sebebi netleşmedi") and ek[0].startswith("Kurun cumaki"), ek
    uzak = temel + "<p>Bir. İki. Kurun hızlanması eşlik etmedi. Sebebi netleşmedi.</p>"
    _t, ek = uret._okuma_sec(uzak, 330)
    assert not ek, f"bitişik olmayan çekince seçildi: {ek}"


def _u10_esik_blogu():
    """U10: günlük "Neye bakılacak" — risk bölümünden en çok 2 madde, madde
    başına ≤170, kalıp `<strong>tetik</strong> → etki; izlenecek: ölçü`. Risk
    gündem döngüsüne girmez; takvimde anılan yayıma işaret eden, kalıba uymayan,
    sığmayan ve fikir seviyesi taşıyan madde düşer — hepsi DUSEN'de görünür.
    Blok Beklenen'i kırpmaz."""
    b = _gunluk_fikstur()
    b["gundem"]["risk"] = (
        "<ul><li><strong>Yüksek aylık TÜFE</strong> → kısa uç; izlenecek: 2 yıllık getirinin %40,5'in üstüne dönmesi.</li>"
        "<li>Kalıba uymayan serbest madde.</li>"
        "<li><strong>Euroda siyaset</strong> → euro/TL; izlenecek: Fransa–Almanya farkının 130 bp'nin üstünde kalması.</li>"
        "<li><strong>Distilat oranı</strong> → ürün; izlenecek: oranın 0,0480'i aşması.</li>"
        "<li><strong>Uzun madde</strong> → " + "çok uzun etki " * 15 + "; izlenecek: bir ölçü.</li>"
        "<li><strong>Kuzey Denizi grevi</strong> → Brent; izlenecek: Forties kesintisi.</li>"
        "<li><strong>Üçüncü uyan</strong> → kur; izlenecek: günlük çıkış.</li></ul>")
    b["fikirler"] = [{"baslik": "x", "giris": 0.044021, "hedef": 0.0392, "stop": 0.048, "ondalik": 4}]
    t = uret.bulten_zinciri(b)[0]
    blok = t.split("Neye bakılacak\n")[1].split("\n\n")[0].split("\n")
    assert blok == ["· Euroda siyaset → euro/TL; izlenecek: Fransa–Almanya farkının 130 bp'nin üstünde kalması.",
                    "· Kuzey Denizi grevi → Brent; izlenecek: Forties kesintisi."], blok
    neden = " ".join(d[1] for d in uret.DUSEN if d[0] == "risk")
    for iz in ("takvimde zaten anılan", "kalıba uymuyor", "170 karakteri aşıyor", "işlem fikri seviyesi"):
        assert iz in neden, f"düşüş görünmüyor: {iz}"
    assert "\nRisk" not in t and "Beklenen: Salı ve sonrası. Hazine 8 yıllık tahvil satıyor." in t
    # Bölüm doluyken blok boş kalırsa sessiz değil; başlık yalnız basılmaz.
    b["gundem"]["risk"] = "<ul><li>Serbest madde bir.</li></ul>"
    t = uret.bulten_zinciri(b)[0]
    assert "Neye bakılacak" not in t and any("giren madde yok" in d[1] for d in uret.DUSEN)
    assert "Neye bakılacak" not in uret.bulten_zinciri(_haftalik_fikstur())[0], "haftalıkta eşik bloğu"
    # 01.10 sınıfı: dört uzun madde tavanı zorlasa da Beklenen kırpılmaz.
    b["gundem"]["risk"] = "<ul>" + "".join(
        f"<li><strong>Tetik {i}</strong> → etki; izlenecek: ölçü {i} ve uzunca bir açıklama.</li>" for i in range(4)) + "</ul>"
    b["ozet"]["ne_oldu"] = "<ul>" + ("<li>" + "Madde %2,1 uzun cümle burada duruyor. " * 8 + "</li>") * 6 + "</ul>"
    t = uret.bulten_zinciri(b)[0]
    assert "Beklenen: Salı ve sonrası. Hazine 8 yıllık tahvil satıyor." in t and len(t) <= uret.TEK_TAVAN


def _tek_tanimlar():
    """Gönderinin iki ölçüsü başka bir yerdeki tanımın EŞİDİR; ikinci liste bir
    gün sessizce ayrışır. (1) "Aynı sayılar" kalıbı kapının (tweet/denetim)
    kalıbıyla aynı. (2) Olağandışı eşiği sayfanınkiyle (anaSayfa.ts) aynı."""
    kok = Path(__file__).resolve().parents[1]
    dn_src = (kok / "tweet" / "denetim.py").read_text(encoding="utf-8")
    assert uret.OLGU_SAYI.pattern in dn_src, \
        f"tweet/denetim'in 'aynı sayılar' kalıbı üreticininkinden ayrışmış: {uret.OLGU_SAYI.pattern}"
    ts = (kok / "site" / "src" / "lib" / "anaSayfa.ts").read_text(encoding="utf-8")
    m = re.search(r"export const OLAGANDISI_SIGMA\s*=\s*([\d.]+)", ts)
    assert m and float(m.group(1)) == uret.OLAGANDISI_SIGMA, \
        f"olağandışı eşiği sayfayla ayrışmış: sayfa {m and m.group(1)} · gönderi {uret.OLAGANDISI_SIGMA}"


# ── K bölümü (05.10.2026): kapı, düzeltme yanıtı, görsel kilidi, etkileşim ──

_K_NOT = "Ölçüm ve yorumdur; yatırım tavsiyesi değildir."
_K_GOVDE = ("Sabah Notu — 5 Ekim 2026\n\nTÜFE eylülde %2,61 arttı, yıllık oran %33,0. "
            + "Piyasa bugün şu sebeple böyle hareket etti. " * 7)


def _k_engel(metin: str, tur: str = "bulten") -> list[str]:
    import denetim as dn
    return dn.denetle(metin, tur)[0]


def _k_uyari(metin: str, tur: str = "bulten") -> list[str]:
    import denetim as dn
    return dn.denetle(metin, tur)[1]


def _k1_kirpma_izleri():
    """K1: üreticiler '…' üretmez; satır sonundaki her '…', sayıda/sıra sayısında
    kesik ve kapanmamış parantez/tırnak ENGEL. Hassasiyet iki yönlü: ondalık
    cümle sonu, endeks adı, oran ve Türkçe kesme işareti ENGEL ALMAZ."""
    def g(satir: str) -> str:
        return f"{_K_GOVDE}\n\n{satir}\n\n{_K_NOT}"
    # (a) kırpma izleri ENGEL
    for satir, iz in (("Kızıldeniz denizcilik için fiilen kapalı durumda…", "'…'"),
                      ("Kısa uç yükseldi (3 aylık spot %37,64, +35 bp…", "kırpma"),
                      ("Faiz farkı 0,4 puan…", "kırpma"),
                      ("Hareket 2,1σ…", "kırpma"),
                      ("Kısa uç yükseldi (3 aylık spot %37,64 ve uzun uç geriledi.", "kapanmamış"),
                      ('Bakan "bütçe disiplini sürecek dedi.', "kapanmamış"),
                      ("Kurul «faiz sabit dedi.", "kapanmamış"),
                      ("Ölçümün asıl maddesi perşembe: 38.", "sıra sayısında"),
                      ("Yönünü değiştirdi. TCMB'nin 35.", "sıra sayısında")):
        e = _k_engel(g(satir))
        assert any(iz in x for x in e), f"kırpma izi yakalanmadı ({iz}): {satir!r} → {e}"
    # (b) meşru satırlar ENGEL ALMAZ
    for satir in ("Beş yıllık %5,089.", "Getiri = %13.", "Oy dağılımı 6/7.",
                  "Haftanın en sert düşüşü BIST 100.", "Endeks S&P 500.",
                  "TCMB'nin rezervi arttı (brüt 160 milyar dolar).",
                  "Sıralama: 1) kur, 2) faiz.", "Kurul «faiz sabit» dedi.",
                  'Bakan "bütçe disiplini sürecek" dedi.', "Hazine'nin ihalesi yarın."):
        e = [x for x in _k_engel(g(satir)) if "kısa" not in x]
        assert not e, f"meşru satır ENGEL aldı: {satir!r} → {e}"
    # (c) ':' ile biten paragraf UYARI (içeriksiz kısa etiket zaten ENGEL)
    u = _k_uyari(g("Önümüzdeki haftanın iki sınavı ve onları izleyen ölçüler şunlar:"))
    assert any("':' ile bitiyor" in x for x in u), u
    # (d) 'Gündem yok' uyarısı yalnız günlükte: haftalık iskelet Gündem taşımaz
    h = g("Senaryolar\nAna senaryo: kur ritmi sürer.").replace("Sabah Notu", "Haftaya Bakış")
    assert not any("Gündem" in x for x in _k_uyari(h)), "haftalıkta 'Gündem yok' uyarısı"
    assert any("Gündem" in x for x in _k_uyari(g("Kur sakin."))), "günlükte 'Gündem yok' uyarısı düştü"


def _k2_ilk280():
    """K2: bülten gönderisinin ilk 280 karakteri bir ölçüm taşımalı (UYARI);
    analizde sorulmaz. Ölçü üreticinin tanımı (uret._sayilar)."""
    sayisiz = ("Sabah Notu — 5 Ekim 2026\n\n" + "Piyasa bugün şu sebeple böyle hareket etti. " * 8
               + "TÜFE %2,61.\n\n" + _K_NOT)
    assert any("ilk 280" in x for x in _k_uyari(sayisiz)), "sayısız ilk 280 uyarı vermedi"
    assert not any("ilk 280" in x for x in _k_uyari(f"{_K_GOVDE}\n\n{_K_NOT}")), "ölçüm taşıyan açılış uyarı aldı"
    bp = "Sabah Notu — 5 Ekim 2026\n\nFransa Almanya'ya 130 bp ödüyor. " + "Dolgu cümlesi. " * 20 + "\n\n" + _K_NOT
    assert not any("ilk 280" in x for x in _k_uyari(bp)), "birimli tam sayı ölçüm sayılmadı"
    an = sayisiz.replace("Sabah Notu — 5 Ekim 2026", "Analiz — 5 Ekim 2026")
    assert not any("ilk 280" in x for x in _k_uyari(an, "analiz")), "analizde ilk 280 soruldu"


def _k9_bicim_ve_nfkc():
    """K9: matematik kalın harf ENGEL; tavsiye, okur dili ve site izi NFKC'de;
    ters işaret sırası ve yüzde işaretsiz oran UYARI (vade adı ve birimli fark muaf)."""
    def g(c: str) -> str:
        return f"{_K_GOVDE}\n\n{c}\n\n{_K_NOT}"
    e = _k_engel(g("Dolar 𝐚𝐥ı𝐧."))
    assert any("emoji" in x for x in e) and any("tavsiye" in x for x in e), f"kalın harf: {e}"
    e = _k_engel(g("Dolar ａｌıｎ."))                       # tam genişlik: yalnız NFKC yakalar
    assert any("tavsiye" in x for x in e), f"NFKC tavsiye: {e}"
    e = _k_engel(g("Ayrıntısı ｓｉｔｅｄｅ duruyor."))
    assert any("atıf" in x for x in e), f"NFKC site izi: {e}"
    e = _k_engel(g("Değer ｏｚｅｔ．ｊｓｏｎ dosyasından okundu."))
    assert any("okura değil" in x for x in e), f"NFKC okur dili: {e}"
    assert any("işaret yüzden sonra" in x for x in _k_uyari(g("Devalüasyon %+20,9."))), "ters işaret"
    assert not any("işaret yüzden sonra" in x for x in _k_uyari(g("Devalüasyon +%20,9."))), "doğru işaret uyarı aldı"
    assert any("yüzde işaretsiz" in x for x in _k_uyari(g("TÜFE yıllık 31,51 oldu."))), "işaretsiz oran"
    for c in ("On yıllık 4,12 seviyesinde.", "10 yıllık 4,12 seviyesinde.", "İki yıllık 39,5 oldu.",
              "Getiri yıllık 4,1 baz puan arttı.", "Fark yıllık 0,8 puan.", "TÜFE yıllık %31,51 oldu.",
              "Getiri 5–10 yıllık 4,2 bp yükseldi."):
        assert not any("yüzde işaretsiz" in x for x in _k_uyari(g(c))), f"yanlış alarm: {c!r}"


def _k11_tiklanir_ve_gorsel():
    """K11: hashtag, cashtag ve bahsetme ENGEL (link mesajıyla değil); para
    birimi ve rakamlı sembol geçer. Görsel yolu kapalı: --resim durur, gövde
    medya alanı kuramaz, grafik betiği ve PNG'ler yok, iş akışı resim almaz."""
    def g(c: str) -> str:
        return f"{_K_GOVDE}\n\n{c}\n\n{_K_NOT}"
    for c in ("Kurda $TRY sakin.", "$USDTRY yükseldi.", "Bugün #TCMB kararı.", "@TCMB açıkladı.",
              "Getiri $r_t$ ile gösterilir."):
        e = _k_engel(g(c))
        assert any("tıklanır" in x for x in e), f"tıklanır öğe kaçtı: {c!r} → {e}"
        assert not any(x.startswith("link") for x in e), f"tıklanır öğe 'link' diye etiketlendi: {e}"
    assert any("formül" in x for x in _k_engel(g("Getiri $r_t$ ile gösterilir."))), "KaTeX kalıntısı adlanmadı"
    for c in ("Brent, 10 Eylül kapanışı: 107,63 $ oldu.", "S&P 500 %0,4 arttı.", "$XU100 sembolü.",
              "Endeks 5 bin puan; e-posta yok.", "C# değil.", "Oran %12,5."):
        e = [x for x in _k_engel(g(c)) if "tıklanır" in x]
        assert not e, f"yanlış alarm: {c!r} → {e}"
    import gonder
    assert gonder._govde("x", None) == {"text": "x"}, gonder._govde("x", None)
    assert gonder._govde("x", "42") == {"text": "x", "reply": {"in_reply_to_tweet_id": "42"}}
    assert gonder.GOVDE_ALANLARI == frozenset({"text", "reply"}), "gövde alan listesi genişlemiş"
    import io as _io, tokenize as _tk
    kok = Path(__file__).resolve().parents[1]

    def kod(yol: Path) -> str:
        ham = yol.read_text(encoding="utf-8")
        return "".join(t.string for t in _tk.generate_tokens(_io.StringIO(ham).readline)
                       if t.type not in (_tk.COMMENT, _tk.STRING))
    for ad in ("gonder.py", "ozel.py"):
        k = kod(kok / "tweet" / ad)
        assert "media" not in k and "_yukle" not in k, f"tweet/{ad}: medya yolu geri gelmiş"
    oz = (kok / "tweet" / "ozel.py").read_text(encoding="utf-8")
    assert "requests.post(" not in oz and "gonder._gonder_zincir(" in oz, \
        "özel gönderi gövde kilidinden geçmiyor (doğrudan POST)"
    assert not (kok / "tweet" / "grafik_kredi.py").exists(), "grafik betiği geri gelmiş"
    assert not list((kok / "tweet" / "ozel").glob("**/*.png")), "özel gönderi dizininde görsel var"
    yml = "\n".join(l for l in (kok / ".github" / "workflows" / "tweet-ozel.yml").read_text(encoding="utf-8")
                    .splitlines() if not l.lstrip().startswith("#"))    # yorum değil, iş akışının kendisi
    for iz in ("resimler", "grafik_betigi", "--resim", "matplotlib"):
        assert iz not in yml, f"tweet-ozel.yml görsel izi taşıyor: {iz}"
    s = subprocess.run([sys.executable, str(kok / "tweet" / "ozel.py"), "--metin", __file__, "--resim", "a.png"],
                       capture_output=True, text=True, cwd=str(kok))
    assert s.returncode != 0 and "görsel gönderilmez" in (s.stdout + s.stderr), (s.returncode, s.stderr[-200:])


class _SahteYanit:
    def __init__(self, kod: int, veri: dict):
        self.status_code, self._v, self.text = kod, veri, json.dumps(veri)

    def json(self):
        return self._v


def _k5_duzeltme_yaniti():
    """K5: düzeltme yanıtı — tetik açık (gonderi alanı), alt dize eşleşmesi yanıt
    üretmez, kimliksiz hedef düşer, aynı içerik iki dosyada tek gönderi, kısa
    düzeltme kapıdan geçer, yanıt doğru kimliğe gider ve gövdede medya yok."""
    import os
    import analiz as an
    import duzeltme as dz
    import gonder
    bugun = dt.datetime.now(dt.timezone.utc).date()
    dun = (bugun - dt.timedelta(days=1)).isoformat()
    evvel = (bugun - dt.timedelta(days=2)).isoformat()
    kayit = {"tarih": dun, "alan": "Gümüş haftalık değişim", "eski": "−%5,96", "yeni": "−%6,64",
             "sebep": "hafta kapanışı bir seans geriden okunmuştu",
             "gonderi": "bulten:2026-10-04",
             "gonderi_metni": "Gümüşün haftalık değişimi −%5,96 değil −%6,64; hafta kapanışı bir seans geriden okunmuştu."}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bd, ad_, ar = td / "b", td / "a", td / "arsiv"
        for d in (bd, ad_, ar):
            d.mkdir()
        # (1) alt dize tuzağı: gonderi alanı yok, `eski` arşivde başka bir gönderide geçiyor
        (ar / "bulten-2026-09-30.txt").write_text("# bulten:2026-09-30 · z · u\n\nSabah Notu — 30 Eylül 2026\nBrent −%2,56.\n", encoding="utf-8")
        tuzak = {"tarih": dun, "alan": "Gümüş günlük", "eski": "%2,56", "yeni": "%2,61", "sebep": "x"}
        (bd / f"{evvel}.json").write_text(json.dumps({"tarih": evvel, "duzeltmeler": [tuzak, kayit]}), encoding="utf-8")
        # (2) aynı içerik ikinci bir dosyada (alan metni farklı) → tek gönderi
        (bd / f"{dun}.json").write_text(json.dumps({"tarih": dun, "duzeltmeler": [{**kayit, "alan": "Gümüş (XAG)"}]}), encoding="utf-8")
        (ar / "bulten-2026-10-04.txt").write_text("# bulten:2026-10-04 · z · u\n\nHaftaya Bakış — 4 Ekim 2026\nManşet.\n", encoding="utf-8")
        # Tuzağın düşeceği gönderi de KİMLİKLİ: alt dize tetiği geri gelirse yanıt
        # gerçekten üretilebilir olmalı ki sınama onu görsün.
        defter = {"bulten:2026-10-04": {"idler": ["777", "778"], "zaman": "2026-10-04T15:02:06+00:00"},
                  "bulten:2026-09-30": {"idler": ["555"], "zaman": "2026-09-30T04:45:21+00:00"},
                  "bulten:2026-08-31": {"idler": [], "zaman": ""}}
        adaylar, u = dz.adaylar(bugun, defter, bd, ad_)
        assert len(adaylar) == 1 and adaylar[0]["ust"] == "777", adaylar
        assert adaylar[0]["anahtar"] == dz.anahtar("bulten:2026-10-04", "−%5,96", "−%6,64"), adaylar[0]["anahtar"]
        # (3) kimliksiz hedef: aday yok, adıyla uyarı
        (bd / f"{dun}.json").write_text(json.dumps({"tarih": dun, "duzeltmeler": [
            {**kayit, "gonderi": "bulten:2026-08-31", "eski": "a", "yeni": "b"}]}), encoding="utf-8")
        adaylar, u = dz.adaylar(bugun, defter, bd, ad_)
        assert len(adaylar) == 1 and any("kimliksiz" in x for x in u), (adaylar, u)
        # (4) kısa düzeltme kapıdan geçer; başlık hedefin başlığından
        t = dz.metin(adaylar[0], ar)
        assert t.startswith("Düzeltme — Haftaya Bakış, 4 Ekim 2026\n"), t[:60]
        assert len(t) < 200, len(t)
        import denetim as dn
        e, uy = dn.denetle(t, "duzeltme")
        assert not e, f"kısa düzeltme ENGEL aldı: {e}"
        assert any("sayfa yapısı" in x for x in dn.denetle(t.replace("Gümüşün", "Gösterge şeridinde gümüşün"), "duzeltme")[1])
        assert any("başlık" in x for x in dn.denetle(t.replace("Düzeltme — ", "Düzeltiyoruz: "), "duzeltme")[0])
        # (5) analiz ön bilgisi: iç içe liste okunur, gonderi alanı taşınır
        mdx = (f"---\ntitle: 'x'\npubDate: 2026-09-10\nduzeltmeler:\n  - tarih: '{dun}'\n    alan: 'a'\n"
               f"    eski: 'tek öncü'\n    yeni: 'eşzamanlı'\n    gonderi: 'analiz:x-2026-09-10'\n"
               f"    gonderi_metni: 'Kısa düzeltme metni burada duruyor, tam cümle.'\nseviye: 'orta'\n---\nGövde\n")
        (ad_ / "x-2026-09-10.mdx").write_text(mdx, encoding="utf-8")
        d2 = {**defter, "analiz:x-2026-09-10": {"idler": ["900"], "zaman": "z"}}
        a2, _ = dz.adaylar(bugun, d2, bd, ad_)
        an_ad = [x for x in a2 if x["hedef"].startswith("analiz:")]
        assert len(an_ad) == 1 and an_ad[0]["ust"] == "900", a2
        assert dz.metin(an_ad[0], ar).endswith(uret.SORUMLULUK_TEKNIK)
        gercek = dz.on_bilgi_duzeltmeleri(
            (Path(__file__).resolve().parents[1] / "site/src/content/analiz/ppk-karari-2026-09-10.mdx").read_text(encoding="utf-8"))
        assert len(gercek) == 2 and all(k in gercek[0] for k in ("tarih", "alan", "eski", "yeni")), gercek
        # (6) uçtan uca: gonder.main yanıtı doğru kimliğe atar, defter içerik anahtarıyla yazılır,
        #     ikinci koşu aynı düzeltmeyi bir daha atmaz; gövdede medya yok
        (bd / f"{dun}.json").write_text(json.dumps({"tarih": dun, "duzeltmeler": [kayit]}), encoding="utf-8")
        (ad_ / "x-2026-09-10.mdx").unlink()
        dfy = td / "defter.json"
        dfy.write_text(json.dumps(defter), encoding="utf-8")
        govdeler: list[dict] = []
        import requests as _rq
        eski_post, eski_b, eski_a = _rq.post, uret.BULTENLER, an.ANALIZ_DIZIN
        eski_erisim, eski_arsiv, eski_argv = gonder._erisim_al, dz.ARSIV, sys.argv
        eski_env = {k: os.environ.get(k) for k in ("TW_CLIENT_ID", "TW_CLIENT_SECRET", "TW_KILIT", "TW_REFRESH_TOKEN")}
        try:
            def sahte_post(url, json=None, **_):
                govdeler.append(json)
                return _SahteYanit(201, {"data": {"id": str(5000 + len(govdeler))}})
            _rq.post = sahte_post
            uret.BULTENLER, an.ANALIZ_DIZIN, dz.ARSIV = bd, ad_, ar
            gonder._erisim_al = lambda _d: "sahte-jeton"
            for k in eski_env:
                os.environ[k] = "x"
            sys.argv = ["gonder.py", "--tur", "duzeltme", "--defter", str(dfy)]
            import contextlib, io as _io
            with contextlib.redirect_stdout(_io.StringIO()):
                kod = gonder.main()
            assert kod == 0, kod
            assert len(govdeler) == 1, govdeler
            assert govdeler[0]["reply"] == {"in_reply_to_tweet_id": "777"}, govdeler[0]
            assert "media" not in govdeler[0] and govdeler[0]["text"].startswith("Düzeltme — ")
            df = json.loads(dfy.read_text(encoding="utf-8"))
            k = dz.anahtar("bulten:2026-10-04", "−%5,96", "−%6,64")
            assert df[k]["idler"] == ["5001"] and df[k]["yanit"] == "777", df.get(k)
            with contextlib.redirect_stdout(_io.StringIO()):
                assert gonder.main() == 0
            assert len(govdeler) == 1, "aynı düzeltme ikinci kez gönderildi"
            # kanalın kendi kusuru gönderimi düşürmez (sabahın bülteni gider)
            eski_ad = dz.adaylar
            try:
                dz.adaylar = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("bozuk ön bilgi"))
                with contextlib.redirect_stdout(_io.StringIO()) as out:
                    assert gonder.main() == 0
                assert "düzeltme kanalı okunamadı" in out.getvalue(), out.getvalue()[-200:]
            finally:
                dz.adaylar = eski_ad
        finally:
            _rq.post, uret.BULTENLER, an.ANALIZ_DIZIN = eski_post, eski_b, eski_a
            gonder._erisim_al, dz.ARSIV, sys.argv = eski_erisim, eski_arsiv, eski_argv
            for k, v in eski_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _k12_etkilesim_olcumu():
    """K12: okuma hatası gönderimi düşürmez · haftalık sınır · yaş bandı (24s/7g,
    yaş yazılır, kaçan bant uydurulmaz) · hesap adı yok · iş akışında ayrı git add,
    yeni cron yok · okuma gönderimden SONRA ve yalnız jeton alınmışsa."""
    import metrik as mt
    import gonder
    simdi = dt.datetime(2026, 10, 12, 5, 40, tzinfo=dt.timezone.utc)
    defter = {
        "bulten:2026-10-12": {"idler": ["1"], "zaman": "2026-10-11T19:40:00+00:00"},   # 10 sa → yok
        "bulten:2026-10-11": {"idler": ["2"], "zaman": "2026-10-11T04:30:00+00:00"},   # 25 sa → 24s
        "analiz:x":          {"idler": ["3"], "zaman": "2026-10-04T05:00:00+00:00"},   # 8 g, 24s yok → 24s (xapi#4)
        "bulten:2026-09-01": {"idler": ["4"], "zaman": "2026-09-01T04:30:00+00:00"},   # 41 g → yok
        "analiz:kimliksiz":  {"idler": [], "zaman": ""},
    }
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        yol, ar, bd = td / "metrik.json", td / "arsiv", td / "b"
        ar.mkdir(); bd.mkdir()
        (ar / "bulten-2026-10-11.txt").write_text("# bulten:2026-10-11 · z · u\n\nSabah Notu — 11 Ekim 2026\nMetin.\n", encoding="utf-8")
        (bd / "2026-10-11.json").write_text(json.dumps({"surum": 3}), encoding="utf-8")
        istekler: list[dict] = []

        def istek(url, params, erisim):
            istekler.append(params)
            return _SahteYanit(200, {"data": [
                {"id": "2", "public_metrics": {"impression_count": 120, "like_count": 3, "reply_count": 1,
                                               "retweet_count": 0, "quote_count": 0, "bookmark_count": 2}},
                {"id": "3", "public_metrics": {"impression_count": 900, "like_count": 9, "reply_count": 0,
                                               "retweet_count": 2, "quote_count": 1, "bookmark_count": 4}}]})
        r = mt.haftalik("j", defter, yol, simdi, istek, ar, bd)
        k = json.loads(yol.read_text(encoding="utf-8"))
        bant = {(o["anahtar"], o["bant"]) for o in k["olcumler"]}
        assert bant == {("bulten:2026-10-11", "24s"), ("analiz:x", "24s")}, (bant, r)
        assert set(istekler[0]["ids"].split(",")) == {"2", "3"} and "expansions" not in istekler[0], istekler
        o = [x for x in k["olcumler"] if x["kimlik"] == "2"][0]
        assert o["yas_saat"] == 25.2 and o["bicim"] == 3 and o["uzunluk"] == len("Sabah Notu — 11 Ekim 2026\nMetin.")
        assert o["gosterim"] == 120 and o["yer_imi"] == 2 and o["gonderim_saat_tsi"] == "07:30", o
        assert not any("kullanici" in str(x) or "username" in str(x) for x in k["olcumler"])
        # haftalık sınır: altı gün sonra istek yok
        assert "haftalık sınır" in mt.haftalik("j", defter, yol, simdi + dt.timedelta(days=6), istek, ar, bd)
        assert len(istekler) == 1, "haftalık sınır delindi"
        # bir hafta sonra: aynı bant ikinci kez yazılmaz, yeni bant (bulten:10-11 → 7g) yazılır
        mt.haftalik("j", defter, yol, simdi + dt.timedelta(days=7), istek, ar, bd)
        k = json.loads(yol.read_text(encoding="utf-8"))
        assert sorted((o["anahtar"], o["bant"]) for o in k["olcumler"]).count(("analiz:x", "7g")) == 1
        # okuma hataları yutulur, sebebi yazılır, istisna yükselmez
        for hata in (lambda *a: _SahteYanit(402, {"title": "CreditsDepleted"}),
                     lambda *a: _SahteYanit(403, {}),
                     lambda *a: (_ for _ in ()).throw(ConnectionError("ağ yok")),
                     lambda *a: _SahteYanit(200, None)):
            y2 = td / "m2.json"
            if y2.exists():
                y2.unlink()
            r = mt.haftalik("j", defter, y2, simdi, hata, ar, bd)
            assert "etkilenmedi" in r or "ölçüldü" in r, r
            assert json.loads(y2.read_text(encoding="utf-8")).get("son_hata") or "0/" in r, r
        # gonder sarmalayıcısı: metrik modülünün kendi kusuru da gönderimi düşürmez
        eski = mt.haftalik
        try:
            mt.haftalik = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bozuk"))
            import contextlib, io as _io
            with contextlib.redirect_stdout(_io.StringIO()) as out:
                gonder._metrik_oku("j", defter, td / "m3.json")
            assert "etkilenmedi" in out.getvalue(), out.getvalue()
        finally:
            mt.haftalik = eski
    kok = Path(__file__).resolve().parents[1]
    src = (kok / "tweet" / "gonder.py").read_text(encoding="utf-8")
    i_gonder = src.index("idler = _gonder_zincir(zincir, erisim")
    i_metrik = src.index("_metrik_oku(erisim, defter)")
    assert i_metrik > i_gonder and "if erisim is not None" in src[i_metrik - 200:i_metrik], \
        "metrik okuması gönderimden sonra ve yalnız alınmış jetonla değil"
    yml = (kok / ".github" / "workflows" / "tweet.yml").read_text(encoding="utf-8")
    assert re.search(r"^\s*git add tweet/metrik\.json 2>/dev/null \|\| true\s*$", yml, re.M), \
        "metrik.json ayrı bir git add satırında değil"
    assert len(re.findall(r"^\s*- cron:", yml, re.M)) == 3, "tweet.yml cron sayısı değişti (yayın takvimi indeksleri kayar)"


# ── İnceleme (05.10.2026, donmuş 1a87fb37): üretici ve analiz düzeltmeleri ──

def _i1_sira_sayisi_ozel_ad():
    """kapi#2: sıra sayısı + büyük harfli ad ("yılın 7. PPK") cümle sonu
    sayılmaz — satıra "…sıradaki sınav yılın 7." gibi KESİK bir hüküm girmez.
    Ondalık, saat ve rakamla süren cümle bölünmeye devam eder."""
    c = uret.cumleler("…yılın 7. PPK toplantısı geliyor. Kur sakin.")
    assert "PPK" in c[0] and c[0].endswith("geliyor."), c
    assert len(uret.cumleler("Netflix 3. Çeyrek bilançosunu açıklıyor. Hisse düştü.")) == 2
    for metin, ilk in (("Getiri %5,089. Aynı gün düştü.", "Getiri %5,089."),
                       ("Katılımcı sayısı 61. 2 yıllık sakin.", "Katılımcı sayısı 61."),
                       ("Karar 16:45. Türkiye'de sakin.", "Karar 16:45.")):
        assert uret.cumleler(metin)[0] == ilk, (metin, uret.cumleler(metin))
    s = uret._satir_sec(["Para politikasında sıradaki adım yılın 7. PPK toplantısı. "
                         "Kur sakin kaldı ve TL faizi geriledi. Reuters'a göre talep güçlü."], 120,
                        kaynak_oncelik=True)
    assert not ("yılın 7." in s and "PPK" not in s), f"satır sıra sayısında kesik: {s!r}"


def _i2_tipografi_isaret():
    """cikti#14: işaret yüzden ÖNCE ("%+205,3" → "+%205,3"); aralık, yıl-ay
    ve "%5+%3" bozulmaz."""
    assert uret._tipografi("crack %+205,3, sapma %-3,41, toplam %5+%3") \
        == "crack +%205,3, sapma −%3,41, toplam %5+%3", uret._tipografi("crack %+205,3, sapma %-3,41")
    assert uret._tipografi("bant %1,25-%2,10, 2024-05'te +%2,8") == "bant %1,25–%2,10, 2024-05'te +%2,8"


def _i3_pano_sifir_fark():
    """cikti#5 · sartname#5: ölçülmüş farkı hanesinde sıfır olan kart
    (her gün yayımlanan, değeri aylardır aynı politika faizi) Pano'ya da
    Seviyeler'e de girmez; kıyası ölçülemeyen (`fark` None) yeni kart girer;
    sıfır farklı kartlar PANO_EN_COK'un yerini tutmaz."""
    sabit = {"ad": "Politika faizi", "metin": "37,00", "birim": "%", "fark": 0.0, "fark_metin": "",
             "bugun_yeni": True, "veri_tarihi": "02.10.2026", "anahtar": "politika"}
    aofm = dict(sabit, ad="Ağırlıklı ort. fonlama maliyeti", anahtar="aofm")
    yeni = {"ad": "Yeni seri", "metin": "1,23", "birim": "%", "fark": None, "fark_metin": "",
            "bugun_yeni": True, "veri_tarihi": "02.10.2026", "anahtar": "yeni"}
    for haftalik, etiket in ((False, "Pano: "), (True, "Seviyeler: ")):
        t = uret.bulten_zinciri(_gunluk_fikstur(haftalik=haftalik, gostergeler=[sabit, aofm, yeni]))[0]
        satir = next((l for l in t.split("\n") if l.startswith(etiket)), "")
        assert "Politika faizi" not in t and "fonlama maliyeti" not in t, f"sıfır farklı kart girdi: {satir}"
        assert "Yeni seri %1,23" in satir, f"kıyası ölçülemeyen kart düştü: {satir!r}"
    kartlar = [sabit, aofm] + [{"ad": f"Kart {i}", "metin": f"{i},7{i}", "birim": "%", "fark": 0.1,
                                "fark_metin": "+0,10", "bugun_yeni": True, "veri_tarihi": "02.10.2026"}
                               for i in range(1, 6)]
    t = uret.bulten_zinciri(_gunluk_fikstur(gostergeler=kartlar))[0]
    pano = next(l for l in t.split("\n") if l.startswith("Pano: "))
    assert "Kart 5" in pano, f"sıfır farklı kartlar tavandaki yeri tuttu: {pano}"


def _i4_duzeltilen_sigma():
    """cikti#1: aynı sayının düzeltme kaydı bir enstrümanı adıyla AÇIYORSA o
    enstrüman olağandışı hareket diye anılmaz (01.10: gönderinin TEK olağandışı
    satırı, bültenin kendi 'piyasa hareketi değil' dediği +33,7 bp idi). Makas
    kaydı ("Brent–WTI farkı", "Brent − ABD ham petrolü") Brent'i düşürmez;
    değer eşlemesi aranmaz (gönderim anındaki kayıt sayıyı içermiyordu)."""
    def ola(sigma, duzeltmeler):
        piy = {"en_cok_hareket": {"sigma_kip": "gunluk", "sigma": sigma}, "gruplar": []}
        t = uret.bulten_zinciri(_gunluk_fikstur(piyasa=piy, duzeltmeler=duzeltmeler))[0]
        return next((l for l in t.split("\n") if l.startswith("Olağandışı")), "")
    abd = {"ad": "ABD 2 yıllık", "deger": 33.7, "birim": "bp", "sigma": 4.0}
    d01 = [{"alan": "ABD 2 yıllık getiri, 29.09.2026 kapanışı", "eski": "%4,885", "yeni": "—",
            "sebep": "Vadeli kotasyon birikmiş farkı kapattı; piyasa hareketi değil."}]
    assert ola([abd], d01) == "", "bültenin kendi düzelttiği hareket olağandışı satırına girdi"
    l = ola([dict(abd, deger=-27.5, sigma=-2.5), {"ad": "Nikkei 225", "deger": 3.3, "birim": "%", "sigma": 2.2}],
            [{"alan": "ABD 2 yıllık getiri, 01.10 kapanışı ve günlük değişim"}])
    assert "ABD 2 yıllık" not in l and "Nikkei 225 +%3,30" in l, l
    brent = {"ad": "Brent", "deger": 4.1, "birim": "%", "sigma": 2.5}
    for alan in ("Brent–WTI farkı, 18.09.2026", "Brent − ABD ham petrolü farkı"):
        assert "Brent +%4,10" in ola([brent], [{"alan": alan}]), f"makas kaydı Brent'i düşürdü: {alan}"
    assert ola([brent], [{"alan": "Brent, 2 Ekim kapanışı"}]) == "", "düz düzeltme kaydı eşleşmedi"


def _i5_fikir_seviyesi_tam_sayi():
    """cikti#2: fikir seviyesi SAYI olarak kıyaslanır; bp fikrinin tam sayı
    yazımı ("71 bp", "−250 bp") eşik bloğundan ve senaryodan düşer; tam sayı
    yalnız fikrin birimiyle eşleşir ("47 bin varil", "71,8 milyar" düşmez)."""
    fik = [{"baslik": "x", "birim": "bp", "ondalik": 1, "giris": 57.5, "hedef": 71.0, "stop": 47.0},
           {"baslik": "y", "birim": "bp", "ondalik": 1, "giris": -371.0, "hedef": -250.0, "stop": -460.0}]
    b = _gunluk_fikstur(fikirler=fik)
    b["gundem"]["risk"] = (
        "<ul><li><strong>ABD uzun uç arzı</strong> → 5s30s eğim; izlenecek: 5s30s'nin 71 bp'yi aşması ya da 47 bp'nin altına dönmesi.</li>"
        "<li><strong>TL eğri</strong> → kısa uç; izlenecek: 2y–5y farkının −250 bp'ye daralması.</li>"
        "<li><strong>OPEC+ kesintisi</strong> → Brent; izlenecek: 47 bin varillik kesinti.</li>"
        "<li><strong>Kredi</strong> → banka; izlenecek: 71,8 milyar liralık stok.</li></ul>")
    t = uret.bulten_zinciri(b)[0]
    blok = t.split("Neye bakılacak\n")[1].split("\n\n")[0]
    assert "71 bp" not in blok and "−250 bp" not in blok, f"fikir seviyesi bloğa girdi: {blok}"
    assert "47 bin varillik" in blok and "71,8 milyar" in blok, f"birimi tutmayan sayı düşürüldü: {blok}"
    neden = [d[1] for d in uret.DUSEN if d[0] == "risk" and "işlem fikri seviyesi" in d[1]]
    assert len(neden) == 2, neden
    hb = _haftalik_fikstur(fikirler=fik)
    hb["gundem"]["risk"] = ("<h3>Ana senaryo: eğri dikleşir</h3><p>5s30s 60 bp civarında kalır.</p>"
                            "<h3>Kuyruk: uzun uç arzı</h3><p><strong>Tetik.</strong> 5s30s 71 bp'yi aşar.</p>")
    th = uret.bulten_zinciri(hb)[0]
    assert "Kuyruk:" not in th and any("işlem fikri seviyesi" in d[1] for d in uret.DUSEN), \
        "tam sayı yazımlı fikir seviyesi senaryo satırında kaldı"


def _i6_kaynak_ilk_paragraf():
    """cikti#3: kaynak önceliği yalnız satırın etiketini taşıyan İLK paragraftan;
    kaynaksız seçim bitişik — sığmayan cümleden sonraki kısa cümle seçilmez,
    satır paragraflar arası bir kolaja dönmez."""
    dolgu = "Bu dolgu cümlesi yeterince uzun ve bir şey söylemiyor ama yer tutuyor. "
    b = _gunluk_fikstur()
    b["gundem"]["turkiye"] = ("<p><strong>TL faizi.</strong> 2 yıllık %40,15'e indi. " + dolgu * 4 + "</p>"
                              "<p><strong>Kur.</strong> Reuters'a göre kur yatay.</p>")
    t = uret.bulten_zinciri(b)[0]
    tr = next(l for l in t.split("\n") if l.startswith("Türkiye:"))
    assert "Reuters" not in tr and "Kur." not in tr, f"ikinci paragrafın kaynaklı cümlesi satıra girdi: {tr}"
    s = uret._satir_sec(["TL faizi. 2 yıllık %40,15'e indi.", dolgu * 4, "Kısa son."], 120,
                        esnek=uret.SATIR_ESNEK, kaynak_oncelik=True)
    assert "Kısa son." not in s, f"sığmayan cümleden sonraki kısa cümle seçildi: {s!r}"


def _i7_emtia_bitisik_yedek():
    """cikti#4: kaynak öncelikli seçim yeni sayı taşımayan cümleleri öne alıp
    satırın tek yeni ölçümünü dışarıda bırakırsa (05.10 Emtia: 4,2 dolar
    distilat marjı) bitişik seçime dönülür; yeni sayı varsa satır kalır."""
    b = _gunluk_fikstur()
    b["ozet"]["ne_oldu"] = ("<ul><li><strong>Ürün fiyatları.</strong> Dizel ve benzin vadelileri hafta sonu "
                            "kapanışında yükseldi.</li></ul>")
    b["gundem"]["emtia"] = (
        "<p><strong>Ürün ve ham petrol.</strong> G7'nin stok kararı dizel ağırlıklı ve ilk 20 günde önemli bir "
        "dizel miktarını piyasaya veriyor (Euronews). Cuma distilat marjı 4,2 dolar daraldı, Brent ise yatay "
        "kaldı; karar ham petrolden çok ürünü hedefledi. Hafta sonu Husiler bir Aramco tesisini hedef aldı ve "
        "Hürmüz'de bir tanker vuruldu (Reuters).</p>")
    t = uret.bulten_zinciri(b)[0]
    em = next((l for l in t.split("\n") if l.startswith("Emtia:")), "")
    assert "4,2 dolar" in em, f"satırın tek yeni ölçümü düştü: {em!r} · {uret.DUSEN}"
    assert not any("aynı konu" in d[1] for d in uret.DUSEN if d[0] == "emtia"), uret.DUSEN


def _i8_madde_etiketi():
    """dogruluk#3: maddenin kalın etiketi ilk cümlesine bağlıdır; ilk cümle
    bütçeyi aşarsa ya da atıf yüzünden düşerse içeriksiz "· Rezerv." satırı
    BASILMAZ — madde bütünüyle düşer ve DUSEN'de görünür."""
    uzun = "Swap hariç net rezerv " + "haftalık olarak ve ayrıntılı biçimde ölçülerek " * 9 + "geriledi."
    for haftalik, sinir in ((True, uret.MADDE_SINIR_HAFTA), (False, uret.MADDE_SINIR)):
        b = (_haftalik_fikstur if haftalik else _gunluk_fikstur)()
        b["ozet"]["ne_oldu"] = (f"<ul><li><strong>Rezerv.</strong> {uzun} İkinci cümle %1,1.</li>"
                                "<li><strong>Kur.</strong> Dolar/TL %0,23 arttı.</li></ul>")
        assert len(uzun) > sinir
        t = uret.bulten_zinciri(b)[0]
        assert not re.search(r"^· [^.\n]{1,40}\.$", t, re.M), f"içeriksiz etiket satırı: {t[:400]}"
        assert "· Kur. Dolar/TL %0,23 arttı." in t, "sığan madde değişti"
        assert any(d[0] == "ne_oldu" and "Rezerv." in d[1] for d in uret.DUSEN), "düşen madde DUSEN'de yok"
    b = _gunluk_fikstur()
    b["ozet"]["ne_oldu"] = ("<ul><li><strong>Rezerv.</strong> Ayrıntısı piyasa fotoğrafında.</li>"
                            "<li><strong>Kur.</strong> Dolar/TL %0,23 arttı.</li></ul>")
    t = uret.bulten_zinciri(b)[0]
    assert "· Rezerv." not in t, "atıf düşünce etiket yalnız kaldı"


def _i9_beklenen_tasan():
    """sartname#2: Beklenen'in güvenceli payı aşan takvim cümleleri SİLİNMEZ —
    en düşük öncelikle girer; gönderi tavanın altındaysa gönderide, değilse
    DUSEN'de görünür. Uzun takvim Gündem'i ve Neye bakılacak'ı yerinden etmez."""
    b = _gunluk_fikstur()
    b["gundem"]["takvim"] = (
        "<p><strong>Bugün 10:00 · TÜFE ve Yİ-ÜFE (Eylül).</strong> " + "Ağustos'ta aylık TÜFE %1,84'tü ve okuma uzun. " * 14 + "</p>"
        "<p><strong>Bugün 17:00 · ABD ISM hizmet (Eylül).</strong> Ağustos'ta 55,4'tü. İstihdamın zayıflığı "
        "hizmetlere yansırsa ABD kısa ucu iner ve iki yıllık getiri haftanın dibine doğru çekilir; güçlü bir "
        "okuma ise uzun uca baskı yapar ve vade primini yeniden açar, eğri dikleşmeyi sürdürür.</p>"
        "<p><strong>Salı ve sonrası.</strong> Hazine 8 yıllık tahvil satıyor.</p>")
    t = uret.bulten_zinciri(b)[0]
    dusen = " ".join(d[1] for d in uret.DUSEN)
    for c in ("İstihdamın zayıflığı hizmetlere yansırsa", "Hazine 8 yıllık tahvil satıyor."):
        assert c in t or c in dusen, f"takvim cümlesi sessizce düştü: {c}"
    assert len(t) < uret.TEK_TAVAN - 400 and "İstihdamın zayıflığı" in t, "boş yer varken taşan takvim cümlesi girmedi"
    assert any(d[1].startswith("takvim payı: ") for d in uret.DUSEN), "'Bugün' payını aşan cümle DUSEN'de yok"
    b = _gunluk_fikstur()
    b["gundem"]["takvim"] += "".join(f"<p><strong>{g}.</strong> " + "Uzak takvim cümlesi %1,1 ile uzun anlatılıyor. " * 6
                                     + "</p>" for g in ("Çarşamba", "Perşembe", "Cuma", "Ötesi"))
    b["ozet"]["ne_oldu"] = "<ul>" + ("<li>Madde %2,1 uzun cümle burada duruyor. " * 8 + "</li>") * 6 + "</ul>"
    t = uret.bulten_zinciri(b)[0]
    assert "\nGündem\n" in t and "Neye bakılacak" in t, "uzak takvim cümleleri Gündem'i ya da eşik bloğunu yerinden etti"
    assert len(t) <= uret.TEK_TAVAN


def _i10_takvim_iki_yonlu():
    """cikti#6: haftalık gün satırının iki yönlü sonuç işareti — koşul eki,
    'ise', üst/alt çifti. Kuralın kendi örneği ve 'güçlü gelirse … zayıf
    gelirse' temiz; 04.10'un beş gün satırı işaretlenir; 'Borsa', 'hisse',
    'Fransa', 'neredeyse' işaret sayılmaz; işaretsiz gün DUSEN'de görünür."""
    temiz = ("TÜİK TSİ 10:00'da eylül TÜFE'sini yayımlıyor; beklenti üstü bir aylık rakam kısa ucu yükseltir, "
             "altı indirim fiyatlamasını güçlendirir.",
             "TÜİK 10:00'da veri yayımlıyor; önceki %1,84, güçlü gelirse kısa uç yükselir, zayıf gelirse indirim "
             "fiyatlaması güçlenir.",
             "Tutanak sert bir ton taşırsa ekim artırımı geri gelir; yumuşak bir ton uzun ucu ayırır.")
    for x in temiz:
        assert uret.iki_yonlu_mu(x), x
    tek = ("Pazartesi 5 Ekim: Haftanın ağırlığı ilk gününde. TÜİK 10:00'da eylül TÜFE ve Yİ-ÜFE'sini yayımlıyor; "
           "ağustos okumaları aylık %1,84 ve %2,57'ydi.",
           "Çarşamba 7 Ekim: Fed'in 15–16 Eylül toplantısının tutanakları 21:00'de yayımlanıyor (investingLive).",
           "Cuma 9 Ekim: TÜİK ağustos sanayi üretimini yayımlıyor. Reel kredi büyümesi −4,9 puanla daralmada; sanayi "
           "üretiminde aylık düşüş, kredi sıkılığının üretime geçtiğinin ilk ölçüsü olur.",
           "Borsa İstanbul'da hisse satışı neredeyse bitti; Fransa ve Bursa sakin.",
           "Brent eylülde 100 doların üstünde kaldı.")
    for x in tek:
        assert not uret.iki_yonlu_mu(x), x
    hb = _haftalik_fikstur()
    hb["gundem"]["takvim"] += ("<p><strong>Ötesi.</strong> Planı değişen takvim.</p>"
                               "<p><strong>Cumartesi 10 Ekim.</strong> OPEC+ toplantısı yapılıyor.</p>")
    uret.bulten_zinciri(hb)
    isaret = [d[1] for d in uret.DUSEN if "iki yönlü" in d[1]]
    assert isaret == ["Cumartesi 10 Ekim: gönderiye giden cümle iki yönlü sonuç taşımıyor"], isaret


def _i11_serit_ayraci():
    """cikti#9: rakam şeridinde değer ile etiket uzun tireyle ayrılır; etiketi
    rakamla ya da zaman sözcüğüyle başlayan kalem değere yapışmaz."""
    import analiz as an
    k, _ = an.serit_kalemleri([("−12 bp", "6 aylık düğüm"), ("%13,7", "bir ayda 30 bp'den hızlı açılma")], "")
    assert k == ["−12 bp — 6 aylık düğüm", "%13,7 — bir ayda 30 bp'den hızlı açılma"], k


def _i12_kanit_satiri_en_son():
    """cikti#10: tavanda tablo satırları sondan düşer ama "Kanıtın gücü" satırı
    EN SON düşer — gövdedeki iddiaların çekincesidir."""
    import analiz as an
    dolgu = "Ölçülen sayı bu satırda duruyor ve cümle yeterince uzundur. " * 6
    satirlar = [(f"Soru {i}", f"Satırın kendi ölçümü %{i}0,5 düzeyinde. " + dolgu) for i in range(1, 9)]
    satirlar.append(("Kanıtın gücü", "Orta. Haber satırları ikinci el ve bağımsız doğrulanmadı."))
    sahte = {"tez": "Tez cümlesi %1,25 taşır. " + "Tez cümlesi. " * 60, "satirlar": satirlar, "rakamlar": []}
    eski = an.yonetici_ozeti
    an.yonetici_ozeti = lambda _g: sahte
    try:
        t = an.analiz_zinciri({"slug": "sinama-2026-10-05", "govde": "", "title": "5 Ekim 2026 Sınama — kanıt",
                               "pubDate": "2026-10-05"})[0]
        dusen = list(uret.DUSEN)
    finally:
        an.yonetici_ozeti = eski
    assert "Kanıtın gücü: Orta. Haber satırları ikinci el" in t, "kanıt satırı tavanda düştü"
    assert "Soru 8:" not in t and any(b == "analiz-bütçe" and c.startswith("Soru 8:") for b, c in dusen), \
        f"kanıt dışı son satır düşmedi ya da görünmüyor: {dusen[:3]}"
    assert t.index("Soru 1:") < t.index("Kanıtın gücü:"), "satır sırası değişti"


def _i13_tez_uyarisi_yayindan_once():
    """sartname#8: "tezin ilk cümlesi ölçüm taşır" analiz sınavında da UYARI
    (5 Ekim 2026'dan itibaren, geriye yürümez) ve gönderinin tezini kuran yolun
    AYNISINDAN beslenir; her tarihte çalışan önizleme uyarıyı basar."""
    kok = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(kok / "site" / "tools"))
    try:
        import analiz_sinavi as asv
    finally:
        sys.path.remove(str(kok / "site" / "tools"))
    govde = ('\n<div class="yonetici">\n<p class="tez">Karar sürprizsiz, metin ise tek yönlü değil. '
             'Politika faizi %37,0.</p>\n</div>\n')
    with tempfile.TemporaryDirectory() as td:
        sonuc = {}
        for tarih in ("2026-10-05", "2026-09-10"):
            yol = Path(td) / f"sinama-{tarih}.mdx"
            yol.write_text(f"---\ntitle: \"x\"\npubDate: {tarih}\nozet: \"x\"\n---\n{govde}", encoding="utf-8")
            _e, u, _y = asv.sina(yol)
            sonuc[tarih] = [x for x in u if "tezin ilk cümlesi" in x]
    assert sonuc["2026-10-05"], "analiz sınavı sayısız tez açılışını uyarmadı"
    assert not sonuc["2026-09-10"], "kural geriye yürüdü (yayımlanmış yazıya kapanamaz uyarı)"
    import analiz as an
    assert "tez_uyarisi" in (kok / "site" / "tools" / "analiz_sinavi.py").read_text(encoding="utf-8")
    r = subprocess.run([sys.executable, str(kok / "tweet" / "analiz.py"), "ppk-karari-2026-09-10"],
                       capture_output=True, text=True, timeout=120,
                       env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert r.returncode == 0 and "tezin ilk cümlesi ölçüm sayısı taşımıyor" in r.stdout, \
        f"önizleme uyarıyı yuttu: {r.stdout[-300:]} {r.stderr[-300:]}"
    assert an.tez_uyarisi({"slug": "s", "govde": govde}) and not an.tez_uyarisi(
        {"slug": "s", "govde": govde.replace("Karar sürprizsiz,", "Karar %37,0'de sürprizsiz,")})



def _m1_analiz_duzeltme_yaniti():
    """Kullanıcı kararı 05.10.2026: analiz ön bilgisindeki X düzeltme yanıtı
    YAZILDIĞI GÜN tweet kapısından geçer (analiz sınavında UYARI). Bülten kaydı
    bunu yazma anında `bulten/yaz.py`de yapıyordu; analizde kusur ancak gönderim
    sabahı görünür ve tweet koşusu 21 gün her gün kırmızı biterdi. Uyarı
    siteyi durdurmaz; gonderi alanı olmayan yazı alt süreç bile açmaz."""
    kok = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(kok / "site" / "tools"))
    try:
        import analiz_sinavi as asv
    finally:
        sys.path.remove(str(kok / "site" / "tools"))

    def yazi(td: str, ad: str, kayit: str) -> Path:
        yol = Path(td) / f"{ad}.mdx"
        yol.write_text("---\ntitle: 'x'\npubDate: 2026-10-05\nozet: 'x'\nduzeltmeler:\n"
                       "  - tarih: '2026-10-05'\n    alan: 'hedef üstü kalem oranı'\n"
                       "    eski: '%83,1'\n    yeni: '%78,4'\n" + kayit + "---\n\ngövde\n",
                       encoding="utf-8")
        return yol
    hedef = "    gonderi: 'analiz:tufe-eylul-ppk-2026-09-03'\n"
    with tempfile.TemporaryDirectory() as td:
        temiz = yazi(td, "temiz", hedef + "    gonderi_metni: 'Hedef üstü kalem oranı %83,1 değil %78,4: "
                     "Ağustos yayılım ölçüleri Aralık 2025 verisinden okunmuştu.'\n")
        kirli = yazi(td, "kirli", hedef + "    gonderi_metni: 'Ayrıntı x.com/tto adresinde; dolar alın. "
                     "Oran %83,1 değil %78,4.'\n")
        yarim = yazi(td, "yarim", hedef)
        yok = yazi(td, "yok", "")
        assert not [x for x in asv.duzeltme_yaniti(temiz) if x.startswith("ENGEL")], \
            f"temiz düzeltme yanıtı ENGEL aldı: {asv.duzeltme_yaniti(temiz)}"
        _e, u, _y = asv.sina(kirli)
        assert any(x.startswith("X düzeltme yanıtı: ENGEL") for x in u), f"kirli yanıt yakalanmadı: {u}"
        assert not _e or not any("düzeltme yanıtı" in x for x in _e), "düzeltme yanıtı siteyi durduruyor (ENGEL)"
        assert any("birlikte yazılır" in x for x in asv.duzeltme_yaniti(yarim)), "yarım kayıt uyarısız"
        _e, u, _y = asv.sina(yok)
        assert not [x for x in u if "düzeltme yanıtı" in x], "gonderi alanı olmayan yazıya uyarı"
    # Ayrıştırıcı ve metin gönderimle AYNI yoldan: ikinci bir tanım yok.
    kaynak = (kok / "tweet" / "duzeltme.py").read_text(encoding="utf-8")
    assert "def sina_analiz" in kaynak and "on_bilgi_duzeltmeleri(ham)" in kaynak

# ── İnceleme (05.10.2026, donmuş 1a87fb37): kapı, düzeltme ve gönderim katmanı ──

def _sahte_gonderim(bd: Path, ad_: Path, ar: Path, dfy: Path, post, get=None,
                    argv: list[str] | None = None, gercek_defter: bool = False):
    """gonder.main'i ağsız koşturur: dizinler, jeton, requests ve metrik sahte.
    `gercek_defter`: gonder.DEFTER/ARSIV geçici yola alınır ki defter yolu
    'gerçek defter' sayılsın (metrik ve arşiv dalları koşsun) ama depoya
    hiçbir şey yazılmasın. (kod, çıktı, metrik çağrıları) döner."""
    import os
    import contextlib, io as _io
    import analiz as an
    import duzeltme as dz
    import gonder
    import requests as _rq
    metrik: list = []
    eski = (_rq.post, _rq.get, uret.BULTENLER, an.ANALIZ_DIZIN, gonder._erisim_al, dz.ARSIV,
            sys.argv, gonder._metrik_oku, gonder.DEFTER, gonder.ARSIV)
    eski_env = {k: os.environ.get(k) for k in ("TW_CLIENT_ID", "TW_CLIENT_SECRET", "TW_KILIT", "TW_REFRESH_TOKEN")}
    try:
        _rq.post = post
        if get is not None:
            _rq.get = get
        uret.BULTENLER, an.ANALIZ_DIZIN, dz.ARSIV = bd, ad_, ar
        gonder._erisim_al = lambda _d: "sahte-jeton"
        gonder._metrik_oku = lambda *a, **k: metrik.append(a)
        if gercek_defter:
            gonder.DEFTER, gonder.ARSIV = dfy, ar
        for k in eski_env:
            os.environ[k] = "x"
        sys.argv = argv or ["gonder.py", "--tur", "duzeltme", "--defter", str(dfy)]
        with contextlib.redirect_stdout(_io.StringIO()) as out:
            try:
                kod = gonder.main()
            except SystemExit as e:
                kod = e
        return kod, out.getvalue(), metrik
    finally:
        (_rq.post, _rq.get, uret.BULTENLER, an.ANALIZ_DIZIN, gonder._erisim_al, dz.ARSIV,
         sys.argv, gonder._metrik_oku, gonder.DEFTER, gonder.ARSIV) = eski
        for k, v in eski_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _j1_sira_kesik_mesru():
    """dogruluk#1 · kapi#1 · kapi#3 · sartname#1: saat ("TSİ 14:00."), oran
    ("1:2."), sayım/düzeltme yüklemi ("sayısı 61.", "değil 4.") ve piyasa.py'deki
    sayıyla biten enstrüman adı ("STOXX Europe 600.") ENGEL ALMAZ; gerçek kesik
    ("TCMB'nin 35.", "perşembe: 38.", "Liste: 35.", "Hükümet 12.") ENGEL kalır."""
    import denetim as dn

    def g(satir: str) -> str:
        return f"{_K_GOVDE}\n\n{satir}\n\n{_K_NOT}"
    for satir in ("Basın toplantısı TSİ 15:30.",
                  "Merkez Bankası 22 Ekim'de karar açıklayacak; kararın saati 14:00, basın toplantısı 15:30.",
                  "Karar TSİ 14:00.", "Gündem: ECB 14:15, Fed 21:00.", "Fed tutanakları TSİ 21:00.",
                  "Karar TSİ 16:15, basın toplantısı 16:45.", "Yeni teyit tarihi 3 Eylül 14:30.", "Oran 1:2.",
                  "Ankete katılımcı sayısı 61.", "Haftanın ihale SAYISI 2.", "Tahmin tutmadı: 5 değil 4.",
                  "Dokuz yıllık yalnız 19.", "Avrupa'da en zayıf endeks STOXX Europe 600.",
                  "Haftanın en sert düşüşü BIST 100.", "Çin'de CSI 300."):
        e = [x for x in _k_engel(g(satir)) if "sıra sayısında" in x]
        assert not e, f"meşru satır sıra kesiği sayıldı: {satir!r} → {e}"
    for satir in ("Liste: 35.", "· Plan. Hükümet 12.", "Yönünü değiştirdi. TCMB'nin 35.",
                  "Ölçümün asıl maddesi perşembe: 38.", "Hafta içinde de 36.", "Para ve banka istatistikleri 39."):
        assert any("sıra sayısında" in x for x in _k_engel(g(satir))), f"gerçek kesik kaçtı: {satir!r}"
    # Düzeltme yanıtının doğal kalıbı ("X değil Y.") ENGEL almaz
    t = "Düzeltme — Sabah Notu, 2 Ekim 2026\n\nHaftanın ihale sayısını 3 yazdık, doğrusu 4.\n\n" + _K_NOT
    assert not [x for x in dn.denetle(t, "duzeltme")[0] if "sıra" in x], dn.denetle(t, "duzeltme")[0]
    # piyasa.py METİN olarak: sayıyla biten her enstrüman adının ÖNÜNDEKİ sözcük listede
    kaynak = (Path(__file__).resolve().parents[1] / "bulten" / "piyasa.py").read_text(encoding="utf-8")
    adlar = [a for a in re.findall(r'Varlik\(\s*"[^"]*",\s*"([^"]+)"', kaynak) if re.search(r"\s\d{1,3}$", a)]
    assert len(adlar) >= 5, f"piyasa.py ayrıştırılamadı: {adlar}"
    eksik = [a for a in adlar if a.rsplit(" ", 1)[0].split()[-1].lower() not in dn._ENDEKS_ADI]
    assert not eksik, f"sayıyla biten enstrüman adı endeks listesinde yok: {eksik}"
    for a in adlar:
        assert dn.sira_kesik(f"Günün en zayıfı {a}.") is None, a


def _j2_oran_birimi():
    """kapi#5: "aylık/yıllık + tutar" (milyar, milyon, trilyon, bin, TL, USD)
    işaretsiz oran sayılmaz; çıplak para sözcüğü muaf DEĞİL ("31,51 dolar
    bazında" bir orandır)."""
    def g(c: str) -> str:
        return f"{_K_GOVDE}\n\n{c}\n\n{_K_NOT}"
    for c in ("Cari açık yıllık 40,7 milyar dolara genişledi.", "Aylık 5,2 milyar dolarlık açık.",
              "Gelir yıllık 1,2 trilyon TL oldu.", "Akaryakıt aylık 1,25 TL arttı.",
              "Üretim yıllık 3,2 milyon ton.", "Altın yıllık 2,5 bin ton.", "Fon aylık 7,5 USD."):
        assert not any("yüzde işaretsiz" in x for x in _k_uyari(g(c))), f"tutar oran sayıldı: {c!r}"
    for c in ("Getiri yıllık 31,51 dolar bazında.", "TÜFE yıllık 31,51 oldu.", "Oran yıllık 31,51 binde bir."):
        assert any("yüzde işaretsiz" in x for x in _k_uyari(g(c))), f"işaretsiz oran kaçtı: {c!r}"


def _j3_hashtag_ve_not():
    """kapi#6 · sartname#6(4): hashtag en az bir HARF ister ("#1", "#2026" X'te
    tıklanır değil; "#_TCMB" tıklanır), tam genişlik ＃/＠ NFKC'de yakalanır,
    KaTeX notu yalnız '$' öğesinde."""
    import denetim as dn

    def g(c: str) -> str:
        return f"{_K_GOVDE}\n\n{c}\n\n{_K_NOT}"
    for c, oge in (("Bugün #_TCMB kararı.", "#_TCMB"), ("Bugün #TCMB kararı.", "#TCMB"),
                   ("Bugün ＃TCMB kararı.", "#TCMB"), ("＠TCMB açıkladı.", "@TCMB"), ("Etiket #1_a.", "#1_a")):
        e = [x for x in _k_engel(g(c)) if "tıklanır" in x]
        assert e and repr(oge) in e[0], f"tıklanır öğe: {c!r} → {e}"
    for c in ("Hazine'nin ihale sayısı #1 sırada.", "#2026 yılı."):
        assert not [x for x in _k_engel(g(c)) if "tıklanır" in x], f"yanlış alarm: {c!r}"
    e = [x for x in _k_engel(g("@TCMB_Bilgi duyurusu.")) if "tıklanır" in x]
    assert e and "formül" not in e[0], e
    assert any("formül" in x for x in _k_engel(g("Getiri $r_t ile gösterilir."))), "KaTeX notu düştü"
    assert dn.tiklanir_oge("#TCMB") == "#TCMB"


def _j4_sorumluluk_son_satir():
    """sartname#7: sorumluluk notu gönderinin SON SATIRIDIR — ortaya taşınmış
    not da, notun ardına tek satır sonuyla eklenen satır da ENGEL; üreticilerin
    çıktısı geçer; 'not yok' ile 'yerinde değil' ayrı teşhis."""
    import denetim as dn
    temiz = f"{_K_GOVDE}\n\nGündem: kur sakin, fonlama %37,00.\n\n{_K_NOT}"
    assert not [x for x in dn.denetle(temiz, "bulten")[0] if "sorumluluk" in x], dn.denetle(temiz, "bulten")[0]
    ortada = f"{_K_GOVDE}\n\n{_K_NOT}\n\nGündem: kur sakin, fonlama %37,00."
    e = dn.denetle(ortada, "bulten")[0]
    assert any("son satırda değil" in x for x in e), e
    ekli = temiz + "\nEk satır burada duruyor."
    assert any("son satırda değil" in x for x in dn.denetle(ekli, "bulten")[0]), "notun ardındaki satır geçti"
    yok = dn.denetle(f"{_K_GOVDE}\n\nBitti.", "bulten")[0]
    assert any("sorumluluk notu yok" in x for x in yok) and not any("son satırda" in x for x in yok), yok
    for z in (uret.bulten_zinciri(SAHTE_BULTEN)[0],):
        assert not [x for x in dn.denetle(z, "bulten")[0] if "sorumluluk" in x]


def _j5_duzeltme_penceresi():
    """sartname#4: pencere kaydın KENDİ tarihinden (bülten de analiz gibi): eski
    dosyada bugün tarihli kayıt gider; 22 gün önceki kayıt gitmez ve ADIYLA
    uyarılır; 21 gün önceki gider; defterde olan pencere dışı kayıt uyarı
    üretmez; ileri tarihli kayıt sessizce bekler; tarihsiz analiz kaydı uyarılır."""
    import duzeltme as dz
    bugun = dt.date(2026, 10, 5)
    defter = {"bulten:2026-09-01": {"idler": ["111"], "zaman": "z"}}

    def k(tarih, eski, yeni="y"):
        # Metin kayda özgü: aynı hedefe aynı metin X'te kopya içeriktir ve
        # adaylar onu tek yanıta indirir (xapi#1) — pencere maddesi onu sınamaz.
        return {"tarih": tarih, "alan": "a", "eski": eski, "yeni": yeni, "sebep": "s",
                "gonderi": "bulten:2026-09-01", "gonderi_metni": f"Kısa düzeltme metni {eski}, tam cümle."}
    with tempfile.TemporaryDirectory() as td:
        bd, ad_ = Path(td) / "b", Path(td) / "a"
        bd.mkdir(); ad_.mkdir()
        (bd / "2026-09-01.json").write_text(json.dumps({"duzeltmeler": [k("2026-10-05", "e1")]}), encoding="utf-8")
        (bd / "2026-10-05.json").write_text(json.dumps({"duzeltmeler": [
            k("2026-09-13", "e2"), k("2026-09-14", "e3"), k("2026-10-07", "e4")]}), encoding="utf-8")
        a, u = dz.adaylar(bugun, defter, bd, ad_)
        eskiler = sorted(x["eski"] for x in a)
        assert eskiler == ["e1", "e3"], (eskiler, u)
        assert len(u) == 1 and "2026-09-13" in u[0] and "pencerenin dışında" in u[0] and "bulten:2026-10-05" in u[0], u
        # defterde olan pencere dışı kayıt: uyarı yok
        d2 = {**defter, dz.anahtar("bulten:2026-09-01", "e2", "y"): {"idler": ["9"], "zaman": "z"}}
        assert not dz.adaylar(bugun, d2, bd, ad_)[1], dz.adaylar(bugun, d2, bd, ad_)[1]
        # tarihsiz analiz kaydı: adıyla uyarı
        (ad_ / "x-2026-09-10.mdx").write_text(
            "---\ntitle: 'x'\nduzeltmeler:\n  - alan: 'a'\n    eski: 'e5'\n    yeni: 'y'\n"
            "    gonderi: 'bulten:2026-09-01'\n    gonderi_metni: 'Kısa düzeltme.'\n---\n", encoding="utf-8")
        _, u = dz.adaylar(bugun, d2, bd, ad_)
        assert any("analiz:x-2026-09-10" in x and "tarihi çözülemedi" in x for x in u), u


def _j6_katlanmis_yaml():
    """dogruluk#5: bir analizdeki katlanmış YAML (`sebep: >`) bütün düzeltme
    kanalını kapatmaz — yalnız o dosya düşer; dosya X'e bir şey göndermiyorsa
    uyarı da yok, gonderi'li öğede adıyla uyarı."""
    import duzeltme as dz
    bugun = dt.date(2026, 10, 5)
    defter = {"bulten:2026-10-04": {"idler": ["777"], "zaman": "z"}}
    with tempfile.TemporaryDirectory() as td:
        bd, ad_ = Path(td) / "b", Path(td) / "a"
        bd.mkdir(); ad_.mkdir()
        (bd / "2026-10-05.json").write_text(json.dumps({"duzeltmeler": [{
            "tarih": "2026-10-05", "alan": "a", "eski": "e", "yeni": "y",
            "gonderi": "bulten:2026-10-04", "gonderi_metni": "Kısa düzeltme metni."}]}), encoding="utf-8")
        katli = ("---\ntitle: 'x'\nduzeltmeler:\n  - tarih: '2026-10-01'\n    alan: 'a'\n    sebep: >\n"
                 "      uzun bir gerekçe\n      iki satır\n{ek}---\nGövde\n")
        (ad_ / "ilgisiz-2026-09-10.mdx").write_text(katli.format(ek=""), encoding="utf-8")
        a, u = dz.adaylar(bugun, defter, bd, ad_)
        assert len(a) == 1 and not u, (a, u)
        (ad_ / "ilgisiz-2026-09-10.mdx").write_text(
            katli.format(ek="    gonderi: 'bulten:2026-10-04'\n    gonderi_metni: 'x'\n"), encoding="utf-8")
        a, u = dz.adaylar(bugun, defter, bd, ad_)
        assert len(a) == 1 and len(u) == 1 and "analiz:ilgisiz-2026-09-10" in u[0] and "X'e gitmedi" in u[0], (a, u)


def _j7_yarim_kayit():
    """sartname#6(5): yalnız `gonderi` taşıyan (metinsiz) analiz kaydı aday
    üretmez — boş gövdeli bir "Düzeltme" yanıtı alt sınırdan geçebilirdi."""
    import duzeltme as dz
    bugun = dt.date(2026, 10, 5)
    with tempfile.TemporaryDirectory() as td:
        bd, ad_ = Path(td) / "b", Path(td) / "a"
        bd.mkdir(); ad_.mkdir()
        (ad_ / "x-2026-10-01.mdx").write_text(
            "---\ntitle: 'x'\nduzeltmeler:\n  - tarih: '2026-10-04'\n    alan: 'a'\n    eski: 'e'\n"
            "    yeni: 'y'\n    gonderi: 'analiz:x-2026-10-01'\n---\n", encoding="utf-8")
        a, u = dz.adaylar(bugun, {"analiz:x-2026-10-01": {"idler": ["900"], "zaman": "z"}}, bd, ad_)
        assert a == [] and any("birlikte" in x for x in u), (a, u)


_HEDEF_YOK_GOVDE = {"detail": "You attempted to reply to a Tweet that is deleted or not visible to you.",
                    "title": "Forbidden", "status": 403}


def _j8_hedef_silinmis():
    """dogruluk#6: silinmiş hedefe yanıt 403'ü jeton arızası DEĞİLDİR — kayıt
    terminal ('hedef_yok', kimliksiz) yazılır, arkadaki geçerli düzeltme gider,
    metrik okunur, koşu 0 ile biter; ertesi gün aynı anahtar aday değildir.
    Gövdesi eşleşmeyen 403 bugünkü gibi ölümcül ve kapsam teşhisini korur."""
    import duzeltme as dz
    bugun = dt.datetime.now(dt.timezone.utc).date()

    def kayit(eski, hedef):
        return {"tarih": bugun.isoformat(), "alan": "a", "eski": eski, "yeni": "y", "sebep": "s",
                "gonderi": hedef, "gonderi_metni": f"Düzeltme metni {eski}: doğru değer y, tam cümle."}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bd, ad_, ar = td / "b", td / "a", td / "arsiv"
        for d in (bd, ad_, ar):
            d.mkdir()
        (bd / f"{bugun.isoformat()}.json").write_text(json.dumps({"duzeltmeler": [
            kayit("e1", "bulten:2026-10-04"), kayit("e2", "bulten:2026-10-02")]}), encoding="utf-8")
        defter = {"bulten:2026-10-04": {"idler": ["777"], "zaman": "z"},
                  "bulten:2026-10-02": {"idler": ["888"], "zaman": "z"}}
        dfy = td / "defter.json"
        dfy.write_text(json.dumps(defter), encoding="utf-8")
        govdeler: list = []

        def post(url, json=None, **_):
            govdeler.append(json)
            if (json.get("reply") or {}).get("in_reply_to_tweet_id") == "777":
                return _SahteYanit(403, _HEDEF_YOK_GOVDE)
            return _SahteYanit(201, {"data": {"id": str(6000 + len(govdeler))}})

        def get(url, **_):
            raise AssertionError("silinmiş hedefte /users/me soruldu (jeton teşhisi)")
        kod, out, metrik = _sahte_gonderim(bd, ad_, ar, dfy, post, get, gercek_defter=True)
        assert kod == 0, (kod, out[-300:])
        df = json.loads(dfy.read_text(encoding="utf-8"))
        k1, k2 = dz.anahtar("bulten:2026-10-04", "e1", "y"), dz.anahtar("bulten:2026-10-02", "e2", "y")
        assert df[k1].get("durum") == "hedef_yok" and not df[k1].get("idler") and df[k1]["hedef"] == "777", df[k1]
        assert df[k2]["idler"] and df[k2]["yanit"] == "888", df.get(k2)
        assert "silinmiş ya da görünmüyor" in out and "oauth2.enc" not in out, out[-400:]
        assert len(metrik) == 1, "metrik okuması hedef_yok sonrası koşmadı"
        a, _ = dz.adaylar(bugun, df, bd, ad_)
        assert not a, f"hedef_yok kaydı yeniden aday oldu: {a}"
        # gövdesi eşleşmeyen 403: ölümcül, kapsam teşhisi
        dfy.write_text(json.dumps(defter), encoding="utf-8")

        def post2(url, json=None, **_):
            return _SahteYanit(403, {"detail": "Forbidden", "title": "Forbidden"})

        def get2(url, **_):
            return _SahteYanit(200, {"data": {"username": "u"}})
        kod, out, _ = _sahte_gonderim(bd, ad_, ar, dfy, post2, get2)
        assert isinstance(kod, SystemExit) and "tweet.write" in str(kod), (kod, out[-200:])
    # zincir İÇİ parçanın "görünmez" 403'ü hedef_yok sayılmaz (1 saniye önce
    # atılmış parça geçici görünmez olabilir): yalnız DIŞ hedefte ayrım yapılır
    import gonder
    import requests as _rq
    eski_post, eski_get = _rq.post, _rq.get
    sayac = {"n": 0}

    def post3(url, json=None, **_):
        sayac["n"] += 1
        return (_SahteYanit(201, {"data": {"id": "1"}}) if sayac["n"] == 1
                else _SahteYanit(403, _HEDEF_YOK_GOVDE))
    try:
        _rq.post = post3
        _rq.get = lambda url, **_: _SahteYanit(200, {"data": {"username": "u"}})
        import time as _t
        eski_uyku, _t.sleep = _t.sleep, (lambda *_: None)
        try:
            gonder._gonder_zincir(["a", "b"], "j", ust="777")
        except gonder.HedefYok:
            raise AssertionError("zincir içi parçanın 403'ü hedef_yok sayıldı")
        except SystemExit:
            pass
        else:
            raise AssertionError("zincir içi 403 sessiz geçti")
        finally:
            _t.sleep = eski_uyku
    finally:
        _rq.post, _rq.get = eski_post, eski_get


def _j9_duzeltme_metni_oge_basina():
    """dogruluk#7: düzeltme METNİ öğe başına kurulur — bir adayın kusuru bülteni
    ve öbür adayları durdurmaz; bozuk arşiv dosyasında başlık anahtardan kurulur."""
    import duzeltme as dz
    with tempfile.TemporaryDirectory() as td:
        ar = Path(td)
        (ar / "bulten-2026-10-04.txt").write_bytes("# bulten:2026-10-04 · z · u\n\nHaftaya Bakış — 4 Ekim 2026\n".encode() + b"\xff\xfe\x80")
        assert dz.hedef_basligi("bulten:2026-10-04", ar) == "Haftaya Bakış, 4 Ekim 2026"
    bugun = dt.datetime.now(dt.timezone.utc).date()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bd, ad_, ar = td / "b", td / "a", td / "arsiv"
        for d in (bd, ad_, ar):
            d.mkdir()
        (bd / f"{bugun.isoformat()}.json").write_text(json.dumps({"duzeltmeler": [
            {"tarih": bugun.isoformat(), "alan": "a", "eski": e, "yeni": "y", "gonderi": "bulten:2026-10-04",
             "gonderi_metni": f"Düzeltme metni {e}: doğru değer y, tam cümle."} for e in ("e1", "e2")]}),
            encoding="utf-8")
        dfy = td / "defter.json"
        dfy.write_text(json.dumps({"bulten:2026-10-04": {"idler": ["777"], "zaman": "z"}}), encoding="utf-8")
        govdeler: list = []

        def post(url, json=None, **_):
            govdeler.append(json)
            return _SahteYanit(201, {"data": {"id": str(7000 + len(govdeler))}})
        eski_metin = dz.metin

        def bozuk(ad, *a, **k):
            if ad["eski"] == "e1":
                raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bozuk arşiv")
            return eski_metin(ad, *a, **k)
        try:
            dz.metin = bozuk
            kod, out, _ = _sahte_gonderim(bd, ad_, ar, dfy, post)
        finally:
            dz.metin = eski_metin
        assert kod == 0 and len(govdeler) == 1 and "e2" in govdeler[0]["text"], (kod, govdeler, out[-300:])
        assert "düzeltme metni kurulamadı" in out, out[-300:]


def _j10_metrik_sahte_defterde_yok():
    """sartname#6(6): `--defter` ile verilen (sahte) defterle metrik okuması
    KOŞMAZ — duman api.x.com'a çıkıp gerçek metrik.json'a damga basmasın."""
    bugun = dt.datetime.now(dt.timezone.utc).date()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bd, ad_, ar = td / "b", td / "a", td / "arsiv"
        for d in (bd, ad_, ar):
            d.mkdir()
        (bd / f"{bugun.isoformat()}.json").write_text(json.dumps({"duzeltmeler": [
            {"tarih": bugun.isoformat(), "alan": "a", "eski": "e", "yeni": "y", "gonderi": "bulten:2026-10-04",
             "gonderi_metni": "Düzeltme metni: doğru değer y, tam cümle."}]}), encoding="utf-8")
        dfy = td / "defter.json"
        dfy.write_text(json.dumps({"bulten:2026-10-04": {"idler": ["777"], "zaman": "z"}}), encoding="utf-8")
        kod, out, metrik = _sahte_gonderim(
            bd, ad_, ar, dfy, lambda url, json=None, **_: _SahteYanit(201, {"data": {"id": "1"}}))
        assert kod == 0 and "gönderildi" in out, (kod, out[-200:])
        assert metrik == [], "sahte defterle metrik okuması koştu"


def _j11_kuru_dusen_tam():
    """sartname#2(5): kuru koşu düşen birimlerin TAMAMINI basar; normal koşu
    ilk üçünü özetler."""
    import contextlib, io as _io
    import gonder
    t = f"{_K_GOVDE}\n\nGündem: kur sakin, fonlama %37,00.\n\n{_K_NOT}"
    dusen = [(f"b{i}", f"düşen birim {i} metni") for i in range(5)]
    with contextlib.redirect_stdout(_io.StringIO()) as o:
        gonder.kapidan_gecir([("bulten:2026-10-05", [t], dusen)], tam=True)
    assert all(f"düşen birim {i} metni" in o.getvalue() for i in range(5)), o.getvalue()
    with contextlib.redirect_stdout(_io.StringIO()) as o:
        gonder.kapidan_gecir([("bulten:2026-10-05", [t], dusen)])
    assert "düşen birim 4 metni" not in o.getvalue() and "5 birim" in o.getvalue(), o.getvalue()
    src = (Path(__file__).resolve().parent / "gonder.py").read_text(encoding="utf-8")
    assert "kapidan_gecir(is_listesi, tam=kuru)" in src, "kuru koşu tam dökümü bağlanmamış"


# ── X: X API ve yan kanallar merceği (05.10.2026, donmuş 1a87fb37) ──────────

_KOPYA_GOVDE = {"detail": "You are not allowed to create a Tweet with duplicate content.",
                "title": "Forbidden", "status": 403}


def _x1_ayni_metin_ikizi():
    """xapi#1: aynı hedefe aynı gonderi_metni taşıyan iki kayıt (eski→yeni farklı)
    TEK yanıt üretir. Önce ikincisi X'ten kopya içerik 403'ü alıyor, 403 jeton
    kapsamı sanılıp koşu SystemExit ile düşüyordu: arkadaki geçerli düzeltme ve
    etkileşim okuması gitmiyor, aynı şey 21 gün her sabah tekrarlıyordu. Koşu
    içi ikiz adıyla uyarılır; defterde o hedefe giden metin (gönderildi ·
    gönderiliyor · hedef_yok) ertesi gün yeniden kurulmaz; boşluk/tipografi
    farkı ayrı metin sayılmaz; farklı metin ve farklı hedef etkilenmez."""
    import duzeltme as dz
    bugun = dt.datetime.now(dt.timezone.utc).date()
    ortak = "Gümüş ve altının haftalık değişimi düzeltildi: doğru değerler −%6,64 ve −%1,38."

    def kayit(eski, hedef, metin=ortak):
        return {"tarih": bugun.isoformat(), "alan": eski, "eski": eski, "yeni": "y", "sebep": "s",
                "gonderi": hedef, "gonderi_metni": metin}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bd, ad_, ar = td / "b", td / "a", td / "arsiv"
        for d in (bd, ad_, ar):
            d.mkdir()
        (bd / f"{bugun.isoformat()}.json").write_text(json.dumps({"duzeltmeler": [
            kayit("e1", "bulten:2026-10-04"), kayit("e2", "bulten:2026-10-04"),
            kayit("e3", "bulten:2026-10-02", "Brent kapanışı 66,30 dolardı; 63,21 değil.")]}), encoding="utf-8")
        defter = {"bulten:2026-10-04": {"idler": ["777"], "zaman": "z"},
                  "bulten:2026-10-02": {"idler": ["888"], "zaman": "z"}}
        dfy = td / "defter.json"
        dfy.write_text(json.dumps(defter), encoding="utf-8")
        giden: list[str] = []

        def post(url, json=None, **_):              # X'in kopya içerik kuralı
            if json["text"] in giden:
                return _SahteYanit(403, _KOPYA_GOVDE)
            giden.append(json["text"])
            return _SahteYanit(201, {"data": {"id": str(8000 + len(giden))}})

        def get(url, **_):
            return _SahteYanit(200, {"data": {"username": "u"}})
        kod, out, metrik = _sahte_gonderim(bd, ad_, ar, dfy, post, get, gercek_defter=True)
        assert kod == 0, f"ikiz koşuyu düşürdü: {kod!r} {out[-300:]}"
        assert len(giden) == 2 and any("66,30" in t for t in giden), giden
        assert len(metrik) == 1, "etkileşim okuması koşmadı"
        assert re.search(r"::warning::.*aynı metinle ikinci bir düzeltme kaydı \(alan 'e2'\).*'e1'", out), out[-400:]
        df = json.loads(dfy.read_text(encoding="utf-8"))
        k1, k2 = dz.anahtar("bulten:2026-10-04", "e1", "y"), dz.anahtar("bulten:2026-10-04", "e2", "y")
        assert df[k1]["metin_oz"] == dz.metin_ozu(ortak) and k2 not in df, df
        # ertesi koşu: ikiz yeniden aday OLMAZ (X'e POST yok, uyarı yok)
        kod, out, _ = _sahte_gonderim(bd, ad_, ar, dfy, post, get, gercek_defter=True)
        assert kod == 0 and len(giden) == 2 and "aynı metin" not in out, (kod, giden, out[-300:])
        # defterdeki her durum metni bağlar; boşluk ve tire/eksi farkı aynı metin
        for durum in ({"idler": ["5"], "zaman": "z"}, {"durum": "gönderiliyor", "zaman": "z"},
                      {"durum": "hedef_yok", "hedef": "777", "zaman": "z"}):
            d3 = {**defter, k1: {**durum, "metin_oz": dz.metin_ozu(ortak)}}
            a, u = dz.adaylar(bugun, d3, bd, ad_)
            assert [x["eski"] for x in a] == ["e3"] and not u, (durum, a, u)
        assert dz.metin_ozu("  Brent  kapanışı -%2,1\n idi.") == dz.metin_ozu("Brent kapanışı −%2,1 idi.")
        # farklı metin aynı hedefe gider; aynı metin FARKLI hedefe de gider
        (bd / f"{bugun.isoformat()}.json").write_text(json.dumps({"duzeltmeler": [
            kayit("e1", "bulten:2026-10-04"), kayit("e2", "bulten:2026-10-04", ortak + " Ek kayıt."),
            kayit("e4", "bulten:2026-10-02")]}), encoding="utf-8")
        a, u = dz.adaylar(bugun, defter, bd, ad_)
        assert sorted(x["eski"] for x in a) == ["e1", "e2", "e4"] and not u, (a, u)


def _x4_24s_bandi_okuma_gunu():
    """xapi#4: okuma koşusunda atılan gönderi bir sonraki okumada '24s', ondan
    sonrakinde '7g' alır (önce doğrudan '7g'ye düşüyordu); 7 günü geçmiş ama 24s
    kaydı olmayan gönderi 10 güne kadar '24s' alır, 10 günü geçen '7g'; eski
    cetvelin '7g' kaydına sonradan '24s' yazılmaz. Benzetim: 70 gün, günde bir
    gönderi (0–50 dk gecikme), her gönderimden sonra okuma — 10 günü geçen her
    gönderinin '24s' kaydı var."""
    import random
    import metrik as mt

    def istek(url, params, erisim):
        return _SahteYanit(200, {"data": [{"id": i, "public_metrics": {"impression_count": 1}}
                                          for i in params["ids"].split(",")]})
    t0 = dt.datetime(2026, 10, 12, 5, 40, tzinfo=dt.timezone.utc)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        yol, ar = td / "m.json", td / "ar"
        ar.mkdir()
        defter = {"bulten:2026-10-12": {"idler": ["1"], "zaman": "2026-10-12T05:35:00+00:00"},   # okuma koşusunun gönderisi
                  "bulten:2026-10-11": {"idler": ["2"], "zaman": "2026-10-11T19:40:00+00:00"},   # 10 sa
                  "bulten:2026-09-30": {"idler": ["3"], "zaman": "2026-09-30T05:35:00+00:00"},   # 12 g, 24s yok
                  "bulten:2026-10-03": {"idler": ["4"], "zaman": "2026-10-03T05:35:00+00:00"}}   # 9 g, eski 7g kaydı
        yol.write_text(json.dumps({"surum": 1, "son_deneme": "2026-10-04T05:40:00+00:00", "olcumler": [
            {"anahtar": "bulten:2026-10-03", "bant": "7g", "yas_saat": 170.0}]}), encoding="utf-8")

        def bantlar():
            return {(o["anahtar"], o["bant"]) for o in json.loads(yol.read_text(encoding="utf-8"))["olcumler"]}
        mt.haftalik("j", defter, yol, t0, istek, ar, None)
        assert ("bulten:2026-09-30", "7g") in bantlar() and ("bulten:2026-09-30", "24s") not in bantlar(), bantlar()
        assert ("bulten:2026-10-03", "24s") not in bantlar(), "eski 7g kaydına 24s yazıldı"
        mt.haftalik("j", defter, yol, t0 + dt.timedelta(days=7, minutes=40), istek, ar, None)
        b = bantlar()
        assert ("bulten:2026-10-12", "24s") in b and ("bulten:2026-10-12", "7g") not in b, b
        assert ("bulten:2026-10-11", "24s") in b, b
        mt.haftalik("j", defter, yol, t0 + dt.timedelta(days=14, minutes=55), istek, ar, None)
        assert ("bulten:2026-10-12", "7g") in bantlar(), bantlar()
    random.seed(3)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        yol, ar = td / "m.json", td / "ar"
        ar.mkdir()
        defter = {}
        bas = dt.datetime(2026, 10, 5, 5, 35, tzinfo=dt.timezone.utc)
        for g in range(70):
            an = bas + dt.timedelta(days=g, minutes=random.randint(0, 50))
            defter[f"bulten:{an.date()}"] = {"idler": [str(g + 1)], "zaman": an.isoformat()}
            mt.haftalik("j", defter, yol, an + dt.timedelta(minutes=1), istek, ar, None)
        olc = json.loads(yol.read_text(encoding="utf-8"))["olcumler"]
        var24 = {o["anahtar"] for o in olc if o["bant"] == "24s"}
        son = bas + dt.timedelta(days=69)
        aday = [k for k, v in defter.items() if dt.datetime.fromisoformat(v["zaman"]) < son - mt.UST_24S]
        eksik = [k for k in aday if k not in var24]
        assert len(aday) > 50 and not eksik, f"{len(eksik)}/{len(aday)} gönderide 24s yok: {eksik[:5]}"
        assert max(o["yas_saat"] for o in olc if o["bant"] == "24s") < 24 * 10, "24s bandı 10 günü aştı"


def _x6_gecici_hata_yeniden_deneme():
    """xapi#6: geçici okuma hatası (503 · 429 · ağ/zaman aşımı) haftalık sınırı
    beklemeden en erken 12 saat sonraki koşuda BİR kez daha denenir ve başarıdan
    sonra haftalık ritim döner; kalıcı hata (402 · 403 · 400 · bozuk yanıt)
    haftalık sınırda kalır. Aynı koşuda (12 saat dolmadan) yeniden deneme yok."""
    import requests
    import metrik as mt
    simdi = dt.datetime(2026, 10, 12, 5, 40, tzinfo=dt.timezone.utc)
    defter = {"bulten:2026-10-10": {"idler": ["1"], "zaman": "2026-10-10T05:35:00+00:00"}}

    def tamam(url, params, erisim):
        return _SahteYanit(200, {"data": [{"id": "1", "public_metrics": {"impression_count": 5}}]})

    def firlat(e):
        def f(*_):
            raise e
        return f
    gecici = (lambda *_: _SahteYanit(503, {}), lambda *_: _SahteYanit(429, {}),
              firlat(ConnectionError("ağ yok")), firlat(requests.Timeout("zaman aşımı")))
    kalici = (lambda *_: _SahteYanit(402, {"title": "CreditsDepleted"}), lambda *_: _SahteYanit(403, {}),
              lambda *_: _SahteYanit(400, {}), lambda *_: _SahteYanit(200, None))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ar = td / "ar"
        ar.mkdir()
        for ad, hata, beklenen in [(f"geçici#{i}", h, True) for i, h in enumerate(gecici)] + \
                                  [(f"kalıcı#{i}", h, False) for i, h in enumerate(kalici)]:
            yol = td / f"{ad}.json"
            n = {"i": 0}

            def say(f):
                def g(*a):
                    n["i"] += 1
                    return f(*a)
                return g
            mt.haftalik("j", defter, yol, simdi, say(hata), ar, None)
            assert n["i"] == 1, (ad, n)
            # 12 saat dolmadan (aynı sabahın ikinci koşusu) yeniden deneme yok
            mt.haftalik("j", defter, yol, simdi + dt.timedelta(hours=6), say(tamam), ar, None)
            assert n["i"] == 1, f"{ad}: aynı sabah yeniden denendi"
            mt.haftalik("j", defter, yol, simdi + dt.timedelta(days=1), say(tamam), ar, None)
            assert (n["i"] == 2) is beklenen, f"{ad}: ertesi gün istek {n['i'] - 1} (beklenen {int(beklenen)})"
            k = json.loads(yol.read_text(encoding="utf-8"))
            if beklenen:
                assert k["olcumler"] and "gecici_hata_ani" not in k and "son_hata" not in k, k
                # başarıdan sonra haftalık ritim: altı gün sonra istek yok
                mt.haftalik("j", defter, yol, simdi + dt.timedelta(days=7), say(tamam), ar, None)
                assert n["i"] == 2, f"{ad}: başarıdan sonra haftalık sınır delindi"
            else:
                assert "gecici_hata_ani" not in k and k.get("son_hata"), k
        # geçici hata sürerse her gönderim koşusunda bir deneme (döngü yok)
        yol = td / "surekli.json"
        n = {"i": 0}

        def hep503(*_):
            n["i"] += 1
            return _SahteYanit(503, {})
        for g in range(3):
            mt.haftalik("j", defter, yol, simdi + dt.timedelta(days=g), hep503, ar, None)
        assert n["i"] == 3, n


def _x7_ayni_cift_iki_metin():
    """xapi#7: aynı hedefe aynı eski→yeni çiftiyle iki AYRI metin (depodaki 08.09
    emsali: Altın ve Gümüş, ikisi de '−%0,34'→'−%1,38') tek yanıt üretir ve
    ikinci metin ADIYLA uyarılır (önce sessizce düşüyordu). Aynı kaydın iki
    dosyada çoğalması (metin aynı, alan farklı) uyarı üretmez; kayıt gönderildikten
    sonra metni değişse uyarı pencere boyunca her koşuda basılmaz."""
    import duzeltme as dz
    bugun = dt.date(2026, 10, 5)
    defter = {"bulten:2026-09-08": {"idler": ["111"], "zaman": "z"}}

    def k(alan, metin):
        return {"tarih": "2026-10-05", "alan": alan, "eski": "−%0,34", "yeni": "−%1,38",
                "gonderi": "bulten:2026-09-08", "gonderi_metni": metin}
    altin = k("Altın", "Altının günlük değişimi −%0,34 değil −%1,38.")
    gumus = k("Gümüş", "Gümüşün günlük değişimi −%0,34 değil −%1,38.")
    with tempfile.TemporaryDirectory() as td:
        bd, ad_ = Path(td) / "b", Path(td) / "a"
        bd.mkdir(); ad_.mkdir()
        (bd / "2026-09-08.json").write_text(json.dumps({"duzeltmeler": [altin, gumus]}), encoding="utf-8")
        a, u = dz.adaylar(bugun, defter, bd, ad_)
        assert len(a) == 1 and a[0]["metin_ham"].startswith("Altın"), a
        assert len(u) == 1 and "'Gümüş'" in u[0] and "'Altın'" in u[0] and "eski→yeni" in u[0], u
        # çoğalma: aynı kayıt iki dosyada, alan farklı, metin aynı → uyarı yok
        (bd / "2026-09-08.json").write_text(json.dumps({"duzeltmeler": [altin]}), encoding="utf-8")
        (bd / "2026-10-05.json").write_text(json.dumps({"duzeltmeler": [{**altin, "alan": "Altın (XAU)"}]}), encoding="utf-8")
        a, u = dz.adaylar(bugun, defter, bd, ad_)
        assert len(a) == 1 and not u, (a, u)
        # gönderildikten sonra metin değişti: aday yok, uyarı yok (kronik değil)
        (bd / "2026-10-05.json").write_text(json.dumps({"duzeltmeler": [gumus]}), encoding="utf-8")
        d2 = {**defter, a[0]["anahtar"]: {"idler": ["9"], "zaman": "z", "metin_oz": a[0]["metin_oz"]}}
        a2, u2 = dz.adaylar(bugun, d2, bd, ad_)
        assert not a2 and not u2, (a2, u2)


# ── L: rehber ↔ kod (05.10.2026 belge turu) ──────────────────────────────────
# Rehberin gönderi anatomisini anlatan cümleleri kodun önceliklerini ve
# bütçelerini OKURA (yazara) söyler; ikisi ayrışırsa yazar yanlış cümleyi kısa
# tutar. İlk belge turunda tam bu çıktı: rehber günlük düşme sırasında okumayı
# hiç anmıyordu, haftalık düşme sırası ise hiç yazılı değildi. Sıra kodun
# KENDİSİNDEN ölçülür (`_sigdir` sıfır kapasiteyle, düşen blokların sırası) ve
# rehberdeki ifadelerin metindeki sırasıyla kıyaslanır.

def _gunluk_sira_fikstur() -> dict:
    """Bütün günlük blokları birden fazla birimle kuran sentetik biçim 3 sayısı."""
    uzun = "Bu cümle okumanın ikinci paragrafını tavanın dışına taşır. " * 12
    return {
        "tarih": "2026-10-06", "surum": 3, "gundem_kaynagi": "yazili",
        "manset": "TL eğrisi veriyi bekliyor: 2 yıllık %40,00",
        "ozet": {"ne_oldu": "<ul>" + "".join(
            f"<li><strong>Konu {i}.</strong> Olgu %1,{i}{i} ile ölçüldü. İkinci cümle {i},{i}5.</li>"
            for i in range(1, 4)) + "</ul>"},
        "yorum": "<p>Okumanın ilk cümlesi kısa. İkinci cümle de kısa.</p>"
                 f"<p>Hareketin sebebi netleşmedi. {uzun}</p>",
        "gundem": {
            "takvim": "<p><strong>Bugün 10:00 · TÜFE.</strong> Beklenti %2,18. Yüksek gelirse kısa uç "
                      "yükselir.</p>" + "".join(
                f"<p><strong>Gün {i}.</strong> Yayım {i} gelir. Sonuç {i} iki yönlüdür. "
                + "Uzun bir takvim cümlesi daha yazıldı. " * 3 + "</p>" for i in range(1, 7)),
            "risk": "<ul><li><strong>Avrupa siyaseti</strong> → euro; izlenecek: fark 131 bp.</li>"
                    "<li><strong>Kuzey Denizi grevi</strong> → Brent; izlenecek: kesinti duyurusu.</li></ul>",
            "turkiye": "<p><strong>Eğri.</strong> Kısa uç %37,64 oldu.</p>",
            "kuresel": "<p><strong>ABD.</strong> İstihdam 29,5 bin arttı.</p>"},
        "piyasa": {"en_cok_hareket": {"sigma": [
            {"ad": "Nikkei", "deger": 2.61, "birim": "%", "sigma": 2.7},
            {"ad": "Hang Seng", "deger": -2.63, "birim": "%", "sigma": -2.7}]}},
        "gostergeler": [{"ad": f"Kart {i}", "metin": f"{i},9{i}", "birim": "%", "fark": 0.1,
                         "fark_metin": "+0,10", "bugun_yeni": True, "veri_tarihi": "05.10.2026"}
                        for i in range(1, 4)]}


def _dusme_sirasi(bloklar: list[dict]) -> tuple[list[str], list[str]]:
    """Sıfır kapasitede `_sigdir`: düşen blokların sırası (ardışık tekrarsız) ve
    hiç düşmeyen birimlerin blokları."""
    uret.DUSEN.clear()
    uret._sigdir(bloklar, 0)
    sira: list[str] = []
    for bolum, _ in uret.DUSEN:
        if not sira or sira[-1] != bolum:
            sira.append(bolum)
    kalan = [bl["id"] for bl in bloklar for _ in bl["birim"]]
    return sira, kalan


def _sirali_mi(metin: str, ifadeler: list[str]) -> None:
    konum = -1
    for ifade in ifadeler:
        i = metin.find(ifade, konum + 1)
        assert i > konum, f"rehberde sıra bozuk ya da ifade yok: {ifade!r}"
        konum = i


def _l1_rehber_dusme_sirasi():
    yazim = (uret.KOK / "bulten" / "YAZIM.md").read_text(encoding="utf-8")
    # Günlük: rehberin "Tavan aşılırsa …" cümlesi ↔ `_gunluk3` öncelikleri.
    uret.DUSEN.clear()
    sira, kalan = _dusme_sirasi(uret._gunluk3(_gunluk_sira_fikstur()))
    beklenen = ["takvim", "yorum", "olagandisi", "pano", "gundem", "risk", "yorum",
                "bugun", "takvim", "ne_oldu"]
    assert sira == beklenen, f"günlük düşme sırası rehberden ayrıştı: {sira}"
    assert sorted(kalan) == sorted(["baslik", "ne_oldu", "bugun", "takvim"]), kalan
    i = yazim.index("Tavan aşılırsa önce takvimin payı aşan")
    _sirali_mi(yazim[i:i + 700], [
        "takvimin payı aşan", '"sebebi netleşmedi" devamı', "olağandışı satırı", "sonra pano",
        "gündem satırları", "eşik maddeleri", "okumanın paragrafları", '"Bugün" paragrafının',
        '"Beklenen"in', "ilk maddeden sonraki maddeler", "İlk madde ve"])
    # Haftalık: kural 9'un "Tavan aşılırsa …" cümlesi ↔ `_haftalik3` öncelikleri.
    uret.DUSEN.clear()
    sira, kalan = _dusme_sirasi(uret._haftalik3(_haftalik_fikstur()))
    assert sira == ["pano", "ne_oldu", "takvim", "karne", "senaryo", "ne_oldu"], \
        f"haftalık düşme sırası rehberden ayrıştı: {sira}"
    assert sorted(kalan) == sorted(["baslik", "senaryo", "takvim", "karne"]), kalan
    i = yazim.index("Tavan aşılırsa önce Seviyeler")
    _sirali_mi(yazim[i:i + 400], [
        "Seviyeler", "dördüncü ve sonraki", "takvimin sonraki günleri",
        "karnenin kayıtları", "alternatif", "ilk üç madde", "ana senaryo, takvimin ilk",
        "karnenin sayım satırı düşmez"])


def _l2_rehber_butceleri():
    """Rehberlerin yazara söylediği bütçe sayıları koddaki sabitlerle aynı."""
    import analiz
    bulten = (uret.KOK / "bulten" / "YAZIM.md").read_text(encoding="utf-8")
    analiz_md = (uret.KOK / "analiz" / "YAZIM.md").read_text(encoding="utf-8")

    def tr(n: int) -> str:
        return f"{n:,}".replace(",", ".")
    for ad, deger, metin, kalip in (
        ("MADDE_SINIR", uret.MADDE_SINIR, bulten, "madde başına ~{}"),
        ("BEKLENTI_SINIR", uret.BEKLENTI_SINIR, bulten, "birlikte {}"),
        ("BEKLENTI_TABAN", uret.BEKLENTI_TABAN, bulten, "en az {} karakter"),
        ("ESIK_MADDE", uret.ESIK_MADDE, bulten, "Madde {} karakteri aşmaz"),
        ("SENARYO_SATIR", uret.SENARYO_SATIR, bulten, "en çok {}\n     karakter"),
        ("TEK_TAVAN", uret.TEK_TAVAN, bulten, "{} karakter içinde"),
        ("SATIR_SINIR", analiz.SATIR_SINIR, analiz_md, "satır başına\n     ~{}"),
        ("TEZ_SINIR", analiz.TEZ_SINIR, analiz_md, "tez ~{}"),
        ("TEK_TAVAN", uret.TEK_TAVAN, analiz_md, "tavanı ({})"),
    ):
        ifade = kalip.format(tr(deger))
        assert ifade in metin, f"{ad}={deger}: rehberde {ifade!r} yok"


def main() -> int:
    print("tweet duman sınaması:")
    sina("biçim 3: maddelerle açılır · pano sayfanın kuralıyla · öne çıkanlar yinelenmez", _bicim3_govde)
    sina("analiz gönderisi: yönetici özeti, SABİT <Deger>, atıf düşer, not sonda", _analiz_zinciri)
    sina("kalite kapısı: tavsiye · link · HTML · atıf · kesik · boş etiket · dil · uzunluk", _denetim)
    sina("sorumluluk notu her gönderide, kırpmadan muaf", _kapanis_notu)
    sina("zincirler: uzunluk, HTML sızıntısı, link, yapı bayrağı", _zincirler)
    sina("site atfı yok · gündem girdi · öksüz cümle düştü",
         _site_atfi_ve_gundem)
    sina("site izi sözcük ortasında yakalanmaz (kapasitede ≠ sitede)",
         _site_izi_hassasiyeti)
    sina("kırpma cümle sınırında", _kirpma)
    sina("haftalık gönderi (2. tur): kırpma sayıyla bitmez · günlük satır bölünmez · gün başlığı · ana senaryo",
         _haftalik_gonderi_tur2)
    sina("tavan aşımında satır sondan düşer, düşen satırın ölçümü şeride döner", _tavan_asiminda_rakam_seridi)
    sina("A8 başlık cümle düzeninde: soru '?' ile, isim öbeği ':' ile ('Gelir mi?' · 'Kanıtın gücü:')", _a8_baslik_duzeni)
    sina("A8 şerit: metinde geçmeyen ölçüm · değer önde · işaret sayının parçası · bileşik eşleme · boşsa yok", _a8_serit)
    sina("A8 tezin ilk cümlesi ölçüm taşır (UYARI) · payı aşan tez kesilmez, düşer", _a8_tez_acilisi)
    sina("A8 atıf izi sözcük başında: 'kapasitede' ≠ 'sitede'", _a8_atif_sozcuk_siniri)
    sina("gonder: anahtarsız yeşil, defter mükerrerliği, bayat koruması",
         _gonder_sigortalari)
    sina("jeton kasası: şifreli gidiş-dönüş, yanlış kilit düşer", _jeton_kasasi)
    sina("kalite kapısı öğe başına: kirli düşer, temiz geçer", _kapi_oge_basina)
    sina("gönderim katmanı siteye yazmıyor (X aynası kaldırıldı)", _siteye_sizinti_yok)
    sina("özel gönderi anahtarı: araç kanalıyla aynı biçim, analiz gününde sessiz ozel: yok", _ozel_anahtar)
    sina("U1 tam birim: '…' yok · rakamlı cümle sınırı · parantez · sığmayan birim düşer · tavan kırpmaz", _u1_tam_birim)
    sina("U2 ilk 280: 'Bugün…' paragrafı maddelerin ardına TAŞINIR, Beklenen'den çıkar", _u2_ilk280)
    sina("U3 pano yalnız bugün yeni · değer gövdede yoksa · kur İstanbul 18:00 · σ satırı seansıyla", _u3_pano_ve_olagandisi)
    sina("U4 maddeler öncelikli · taşma sırası · tekrar eden gündem satırı · ara başlık yapışmaz", _u4_maddeler_oncelikli)
    sina("U6 haftalık iskelet: senaryolar · gün gün · karne · seviyeler; tavanda dinamik pay", _u6_haftalik_iskelet)
    sina("U7 kaynaklı cümle öncelikli · 'sebebi netleşmedi' yalnız bitişikse", _u7_kaynak_ve_cekince)
    sina("U10 'Neye bakılacak': kalıp · 2×170 · takvim tekrarı · fikir seviyesi · Beklenen korunur", _u10_esik_blogu)
    sina("tek tanım: aynı-sayı kalıbı kapıyla, olağandışı eşiği sayfayla", _tek_tanimlar)
    sina("K1 kırpma izi ENGEL: satır sonu '…' · sayıda/sıra sayısında kesik · açık parantez/tırnak; meşru sonlar geçer", _k1_kirpma_izleri)
    sina("K2 bülten gönderisinin ilk 280 karakteri ölçüm taşır (UYARI; analizde sorulmaz)", _k2_ilk280)
    sina("K9 kalın harf ENGEL · tavsiye/okur dili/site izi NFKC'de · ters işaret ve işaretsiz oran UYARI", _k9_bicim_ve_nfkc)
    sina("K11 hashtag/cashtag/@ ENGEL ('107,63 $' geçer) · görsel yolu kapalı (--resim, medya alanı, betik, PNG, iş akışı)", _k11_tiklanir_ve_gorsel)
    sina("K5 düzeltme yanıtı: açık tetik · alt dize eşleşmez · kimliksiz düşer · tek gönderi · kısa geçer · doğru kimliğe yanıt", _k5_duzeltme_yaniti)
    sina("K12 etkileşim: okuma hatası gönderimi düşürmez · haftalık sınır · yaş bandı · ayrı git add · cron yok", _k12_etkilesim_olcumu)
    sina("İ kapi#2 sıra sayısı + özel ad cümle sonu değil ('yılın 7. PPK'); ondalık/saat/rakam bölünür", _i1_sira_sayisi_ozel_ad)
    sina("İ cikti#14 işaret yüzden önce ('%+4,5' → '+%4,5')", _i2_tipografi_isaret)
    sina("İ cikti#5 pano/seviyeler: ölçülmüş sıfır fark girmez, ölçülemeyen fark girer, tavanı tutmaz", _i3_pano_sifir_fark)
    sina("İ cikti#1 düzeltme kaydının adıyla açtığı enstrüman olağandışı satırına girmez; makas kaydı düşürmez", _i4_duzeltilen_sigma)
    sina("İ cikti#2 fikir seviyesi sayıyla: '71 bp' · '−250 bp' düşer, '47 bin varil' · '71,8 milyar' kalır", _i5_fikir_seviyesi_tam_sayi)
    sina("İ cikti#3 kaynak önceliği ilk paragrafta; kaynaksız seçim bitişik", _i6_kaynak_ilk_paragraf)
    sina("İ cikti#4 'aynı konu' düşmeden önce bitişik yedek seçim (yeni sayı korunur)", _i7_emtia_bitisik_yedek)
    sina("İ dogruluk#3 madde etiketi ilk cümleye bağlı: içeriksiz '· Rezerv.' basılmaz", _i8_madde_etiketi)
    sina("İ sartname#2 Beklenen payını aşan takvim cümlesi silinmez: boş yerde girer, yoksa DUSEN", _i9_beklenen_tasan)
    sina("İ cikti#6 takvim gün satırı iki yönlü işaret: koşul · ise · üst/alt; tek yönlü gün DUSEN'de", _i10_takvim_iki_yonlu)
    sina("İ cikti#9 şeritte değer ile etiket uzun tireyle ayrılır", _i11_serit_ayraci)
    sina("İ cikti#10 tavanda 'Kanıtın gücü' satırı en son düşer", _i12_kanit_satiri_en_son)
    sina("İ sartname#8 tez açılışı analiz sınavında UYARI (05.10'dan), önizleme uyarıyı basar", _i13_tez_uyarisi_yayindan_once)
    sina("M1 analiz düzeltme yanıtı yazıldığı gün tweet kapısından geçer (UYARI, siteyi durdurmaz)", _m1_analiz_duzeltme_yaniti)
    sina("J dogruluk#1/kapi#1/kapi#3/sartname#1 sıra kesiği: saat · oran · sayım · enstrüman adı geçer, gerçek kesik ENGEL", _j1_sira_kesik_mesru)
    sina("J kapi#5 işaretsiz oran: 'milyar/TL' tutarı oran değil; çıplak 'dolar' muaf değil", _j2_oran_birimi)
    sina("J kapi#6 hashtag harf ister ('#1' değil, '#_TCMB' evet) · tam genişlik · KaTeX notu yalnız '$'", _j3_hashtag_ve_not)
    sina("J sartname#7 sorumluluk notu SON SATIR (ortada ya da ardında satır varsa ENGEL)", _j4_sorumluluk_son_satir)
    sina("J sartname#4 düzeltme penceresi kaydın tarihinden; pencere dışı adıyla uyarılır", _j5_duzeltme_penceresi)
    sina("J dogruluk#5 katlanmış YAML yalnız kendi dosyasını düşürür", _j6_katlanmis_yaml)
    sina("J sartname#6(5) metinsiz düzeltme kaydı aday üretmez", _j7_yarim_kayit)
    sina("J dogruluk#6 silinmiş hedef: terminal kayıt, arkadaki gider, metrik koşar; düz 403 ölümcül", _j8_hedef_silinmis)
    sina("J dogruluk#7 düzeltme metni öğe başına; bozuk arşivde başlık anahtardan", _j9_duzeltme_metni_oge_basina)
    sina("J sartname#6(6) sahte defterle metrik okuması koşmaz", _j10_metrik_sahte_defterde_yok)
    sina("J sartname#2(5) kuru koşu düşen birimlerin tamamını basar", _j11_kuru_dusen_tam)
    sina("X xapi#1 aynı hedefe aynı metin tek yanıt: koşu düşmez, arkadaki gider, metrik koşar, ertesi gün POST yok", _x1_ayni_metin_ikizi)
    sina("X xapi#4 okuma günü gönderisi sonraki okumada 24s (≤10 g), sonra 7g; 70 günlük benzetimde eksik 0", _x4_24s_bandi_okuma_gunu)
    sina("X xapi#6 geçici okuma hatası ertesi koşuda bir kez yeniden denenir; kalıcı hata haftalık sınırda", _x6_gecici_hata_yeniden_deneme)
    sina("X xapi#7 aynı eski→yeni çifti, iki metin: tek yanıt + adıyla uyarı; çoğalma ve sonradan düzeltme sessiz", _x7_ayni_cift_iki_metin)
    sina("L rehber ↔ kod: günlük ve haftalık düşme sırası rehberin cümlesiyle aynı", _l1_rehber_dusme_sirasi)
    sina("L rehber ↔ kod: rehberin bütçe sayıları koddaki sabitler", _l2_rehber_butceleri)
    print(f"\n  {SAYAC['gecti']} geçti · {SAYAC['dustu']} DÜŞTÜ")
    return 1 if SAYAC["dustu"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
