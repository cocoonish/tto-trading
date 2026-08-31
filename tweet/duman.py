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
    except Exception as e:
        SAYAC["dustu"] += 1
        print(f"  ✗ {ad}: {e}")


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
    m = "Cümle bir. " * 100
    k = uret._kirp(m)
    assert len(k) <= uret.SINIR, "kırpma sınırı aşıyor"
    assert k.endswith(".") or k.endswith("…"), f"kırpma ortadan kesti: …{k[-20:]}"


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
        yama = ("import uret; from pathlib import Path; "
                f"uret.BULTENLER = Path({str(bult)!r}); "
                f"uret.TEKNIKLER = Path({str(tekn)!r}); "
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
        assert "KURU" in cikti and "Sabah Bülteni" in cikti or "Haftaya Bakış" in cikti
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


def main() -> int:
    print("tweet duman sınaması:")
    sina("zincirler: uzunluk, HTML sızıntısı, link, yapı bayrağı", _zincirler)
    sina("site atfı yok · gündem girdi · öksüz cümle düştü",
         _site_atfi_ve_gundem)
    sina("kırpma cümle sınırında", _kirpma)
    sina("gonder: anahtarsız yeşil, defter mükerrerliği, bayat koruması",
         _gonder_sigortalari)
    sina("jeton kasası: şifreli gidiş-dönüş, yanlış kilit düşer", _jeton_kasasi)
    print(f"\n  {SAYAC['gecti']} geçti · {SAYAC['dustu']} DÜŞTÜ")
    return 1 if SAYAC["dustu"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
