#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kredi & parasal büyüklükler — duman sınaması. Ağa çıkmaz, saniyeler sürer.

`guncelle.py` bu dosyayı hattın ADIMLARINDAN ÖNCE koşturur; düşerse hat hiç
koşmaz ve siteye kopyalama olmaz. Sınama `--denetle` yazan birinin eline
bırakılmaz: zamanlanmış koşu `--denetle` demez.

BURADAKİ HER MADDE BİR ARIZAYA KARŞILIK GELİR — hepsi 09.09.2026'da bu hattın
kendi dosyalarında ÖLÇÜLDÜ:

  (A) GÜNLÜK SAAT TEK BACAKTAN TÜRÜYORDU. `son_gun` yalnız `usd` sütununa
      bakıyordu; data/gunluk.csv'de kur 08.09'a kadar dolu, analitik bilanço ·
      APİ fonlaması · faiz kotasyonları 04.09'da bitiyordu. Fark yapısal:
      TCMB ertesi iş gününün gösterge kurunu bir gün ÖNCEDEN ilan eder,
      bilanço bir gün GECİKMELİ gelir. Sayfa "günlük aileler 8 Eylül" diyordu,
      yani üç aileyi iki iş günü taze gösteriyordu.
  (B) AYLIK ANKET GÜN YAZIMIYLA BASILIYORDU. `pka_tarih` = "01.08.2026" —
      EVDS aylık gözlemi ayın İLK gününe damgalar ve o damga gün gibi
      yazıldığında okura O GÜN yapılmış bir ölçüm gibi görünür. Biçim
      sözleşmesi (ortak/bicim) aylık saati AA.YYYY ister.
  (C) ÇIPADAN GERİDE KALAN ANAHTARIN SAATİ YOKTU. `zk_ima_oran` 28.08 satırında
      BOŞ (zorunlu karşılık tabanı ~13 gün gecikmeli), son dolu gözlem 21.08;
      kendi tarih anahtarı olmadığı için sayfa onu hattın ana saatiyle (28.08)
      basıyordu. Kusur 12 arşiv sayısının 12'sinde de var.
      Saat yalnız GERİDE kalanlara yazılsaydı anahtar, taban yetiştiği hafta
      özetten DÜŞERDİ — sayfanın adıyla çağırdığı bir anahtarın koşudan koşuya
      var olup olmaması yayın kapısını düşürür (08.09.2026'da DİBS'te tam bu
      sınıftan bir eksik yayını üç kez durdurdu). Bu yüzden ölçü koşulsuz.

Koşum:  python3 duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

import veri
import ozet_uret
import inspect

PROJE = Path(__file__).resolve().parent
GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}" + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


# ---------------------------------------------------------------------------
#  ÇERÇEVE — depodaki o günkü veriden DEĞİL, burada kurulur. Deponun defterini
#  okuyan bir sınama, verinin bugünkü hâline bağımlı olur ve ölçtüğü kuralı
#  değil o günü sınar (08.09.2026'da tam bu kusur ölçüldü).
# ---------------------------------------------------------------------------
def _gunluk_cerceve(kur_son: str, diger_son: str) -> pd.DataFrame:
    """Kur bacağı `kur_son`'a, öbür günlük aileler `diger_son`'a kadar dolu."""
    idx = pd.bdate_range("2026-08-03", kur_son)
    G = pd.DataFrame(index=idx)
    for kol in veri.G_KUR:
        G[kol] = 1.0
    kesim = pd.Timestamp(diger_son)
    for grup in (veri.G_BILANCO, veri.G_FONLAMA, veri.G_FAIZ):
        for kol in grup:
            G[kol] = pd.Series(1.0, index=idx).where(idx <= kesim)
    G.index.name = "tarih"
    return G


def gunluk_saat() -> None:
    print("\n▶ Günlük saat — bağlayıcı bacak (arıza A)")
    G = _gunluk_cerceve("2026-09-08", "2026-09-04")

    veri._DONEM.pop("gun", None)
    aileler = veri.son_gun_aileleri(G)
    sina("aile başına saat ölçülüyor",
         aileler == {"kur": "2026-09-08", "bilanco": "2026-09-04",
                     "api": "2026-09-04", "faiz": "2026-09-04"},
         repr(aileler))

    veri._DONEM.pop("gun", None)
    t = veri.son_gun(G)
    # ARIZA: `_son(G, ["usd"])`'e dönülürse burası 08.09 döner ve düşer.
    sina("son_gun EN ESKİ günlük aileyi verir (kur bacağını değil)",
         t == pd.Timestamp("2026-09-04"), f"{t:%d.%m.%Y}")

    # Ters yön: bütün aileler aynı günde bitiyorsa saat o gündür — kural
    # yalnız ayrışma varken devreye girmeli, her koşuda geri adım atmamalı.
    veri._DONEM.pop("gun", None)
    G2 = _gunluk_cerceve("2026-09-04", "2026-09-04")
    t2 = veri.son_gun(G2)
    sina("aileler aynı gündeyken saat geri adım atmaz",
         t2 == pd.Timestamp("2026-09-04"), f"{t2:%d.%m.%Y}")
    veri._DONEM.pop("gun", None)

    # KAPSAM SÖZLEŞMEDEN TÜRER: günlük kod gruplarına eklenen bir seri
    # ailesiyle birlikte gelmeli, yoksa bağlayıcı saatten sessizce düşer.
    grup_kolon = set(veri.G_KUR) | set(veri.G_BILANCO) | set(veri.G_FONLAMA) | set(veri.G_FAIZ)
    aile_kolon = {k for _, kollar in veri.GUNLUK_AILE.values() for k in kollar}
    sina("günlük kod gruplarının tamamı bir ailede",
         grup_kolon == aile_kolon,
         f"ailesiz: {sorted(grup_kolon - aile_kolon)} · fazla: {sorted(aile_kolon - grup_kolon)}")


# ---------------------------------------------------------------------------
#  ÖZET SÖZLEŞMESİ — ozet_uret.py sentetik bir ölçüm özetiyle GERÇEKTEN koşar.
#  Kaynak metnini okumak yetmez: bu kusurların üçü de yazımda değil ÇIKTIDA
#  görünür (derlenmesi, içe aktarılması ve koşması üç ayrı sınamadır).
# ---------------------------------------------------------------------------
_SENTETIK = {
    "son_hafta": "2026-08-28",
    "son_gun": "2026-09-04",
    "son_gun_aile": {"kur": "2026-09-08", "bilanco": "2026-09-04",
                     "api": "2026-09-04", "faiz": "2026-09-04"},
    "son_ay": "2026-07-01",
    "son_ceyrek": "2026-04-01",
    "pka_tarih": "2026-08-01",
    "pka_yas_gun": 27.0,
    "pka_12a": 23.69,
    "zk_ima_oran": 4.17,
    "carpan_m1": 2.28,
    "aofm": 37.0,
    "aofm_gecerli": True,
    "aofm_tarih": "2026-08-28",
    # zk_ima_oran ÇIPADAN GERİDE, carpan_m1 çıpanın KENDİSİNDE: ikisi de kendi
    # saatini almalı (ölçü koşulsuz — bkz. (C)).
    "anahtar_tarih": {"zk_ima_oran": "2026-08-21", "carpan_m1": "2026-08-28"},
}


def _ozet_kos() -> dict:
    with tempfile.TemporaryDirectory() as td:
        kopya = Path(td) / "Kredi"
        shutil.copytree(PROJE, kopya,
                        ignore=shutil.ignore_patterns("data", "cache", "cikti",
                                                      "__pycache__", "*.pyc"))
        (kopya / "data").mkdir()
        (kopya / "data" / "metrik_ozet.json").write_text(
            json.dumps(_SENTETIK, ensure_ascii=False), encoding="utf-8")
        (kopya / "data" / "veri_durum.json").write_text(
            json.dumps({"uyarilar": []}), encoding="utf-8")
        (kopya / "uyarilar.json").write_text(
            json.dumps({"uyarilar": []}), encoding="utf-8")
        r = subprocess.run([sys.executable, "-u", "ozet_uret.py"], cwd=kopya,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("✗ duman: sentetik çerçevede ozet_uret.py koşmadı\n"
                             + r.stdout + r.stderr)
        return json.loads((kopya / "ozet.json").read_text(encoding="utf-8"))


def ozet_saatleri() -> None:
    print("\n▶ Özet saatleri (sentetik çerçevede ozet_uret.py)")
    o = _ozet_kos()

    sina("gun_tarih bağlayıcı bacaktır", o.get("gun_tarih") == "04.09.2026",
         repr(o.get("gun_tarih")))
    sina("gun okur yazımıyla bağlayıcı bacaktır", o.get("gun") == "4 Eylül 2026",
         repr(o.get("gun")))
    # Taze bacak KAYBOLMAZ: bağlayıcı saat en eskisini yazarken kur bacağı
    # kendi adıyla yayımlanır, sayfa ikisini birlikte söyleyebilsin diye.
    sina("kur bacağı kendi adıyla yayımlanır",
         o.get("gun_kur_tarih") == "08.09.2026", repr(o.get("gun_kur_tarih")))

    # (B) AYLIK SAAT GÜN YAZIMIYLA BASILMAZ.
    sina("pka_tarih AA.YYYY yazımında",
         bool(re.fullmatch(r"\d{2}\.\d{4}", str(o.get("pka_tarih")))),
         repr(o.get("pka_tarih")))

    # (C) HER ANAHTAR KENDİ SAATİNİ TAŞIR — geride kalan da, kalmayan da.
    sina("geride kalan anahtar kendi saatini taşır",
         o.get("zk_ima_oran_tarih") == "21.08.2026",
         repr(o.get("zk_ima_oran_tarih")))
    sina("geride KALMAYAN anahtar da saatini taşır (ölçü koşulsuz)",
         o.get("carpan_m1_tarih") == "28.08.2026",
         repr(o.get("carpan_m1_tarih")))
    # Açıkça yazılmış saat kazanır: geçerlilik süzgecinden geçen AOFM'nin
    # vintajı ayrı hesaplanıyor, mekanik döngü onu EZMEMELİ.
    sina("açık saat mekanik saatin önünde", o.get("aofm_tarih") == "28.08.2026",
         repr(o.get("aofm_tarih")))

    # SAYFA ↔ ÖZET: sayfanın adıyla çağırdığı saat anahtarı üretilmeli.
    mdx = (PROJE.parent.parent / "site/src/content/projeler/kredi-parasal.mdx")
    if mdx.exists():
        cagrilan = set(re.findall(r'anahtar="([a-z0-9_]+_tarih)"',
                                  mdx.read_text(encoding="utf-8")))
        yeni = {"gun_kur_tarih", "zk_ima_oran_tarih", "pka_tarih"} & cagrilan
        eksik = sorted(a for a in yeni if a not in o)
        sina("sayfanın çağırdığı yeni saat anahtarları üretiliyor",
             not eksik, f"eksik: {eksik}")


def bayat_bayragi() -> None:
    """Bayat bayrağı — SAHTE girdiyle, duvar saatinden ve depo verisinden bağımsız.

    NEDEN BURADA. Hattın uçtan uca bayatlık sınavı (`bayatlik_sinavi.py`) var
    ama adı `duman.py` olmadığı için `guncelle.py` onu HİÇ görmüyor; üstelik o
    sınav deponun O GÜNKÜ verisini ve DUVAR SAATİNİ okuyor, yani bayrağın DOĞRU
    açıldığı her gün "ters yön" maddesiyle düşüyor. 10.09.2026'da ölçüldü:
    dokunulmamış ağaçta bayat=True (veri katmanı iki tazelik uyarısı basmış) ve
    sınav "SINAV DÜŞTÜ (ters yön)" veriyor. Bir kapıya bağlansaydı, veriyi
    tazeleyecek koşuyu tam da bayatlık yüzünden durdururdu — yayının önünde
    duran bir denetimin yanlış alarmı arızanın kendisidir.

    Kapı bu yüzden BURADA ve kendi çerçevesini kuruyor. Kardeş hat Fonlama'da
    aynı ayrım 09.09.2026'da yapılmıştı; bu hat o düzeltmeyi almamıştı ve
    bayrağın hiçbir maddesi yoktu.
    """
    print("\n▶ Bayat bayrağı")
    tol = veri.tazelik_tolerans("haftalik")
    taze = ozet_uret.bayat_karari(1, [])
    sina("taze veride bayrak KAPALI ve cümle 'Veri taze' ile başlıyor",
         taze["bayat"] is False and taze["bayat_cumlesi"].startswith("Veri taze"),
         str(taze))
    durmus = ozet_uret.bayat_karari(tol + 30, [])
    sina("durmuş yayımda bayrak AÇIK ve cümle 'BAYAT VERİ' ile başlıyor",
         durmus["bayat"] is True
         and durmus["bayat_cumlesi"].startswith("BAYAT VERİ")
         and "haftalık bacak" in durmus["bayat_cumlesi"], str(durmus))
    # Seri TAZE görünürken önbelleğe düşülmüş olabilir: veri katmanının kendi
    # tazelik uyarısı tek başına bayatlık KANITIDIR.
    enj = ozet_uret.bayat_karari(1, ["TAZELİK: sınav enjeksiyonu — yayın durmuş olabilir."])
    sina("veri katmanının tazelik uyarısı tek başına bayrağı AÇIYOR",
         enj["bayat"] is True and enj["bayat_cumlesi"].startswith("BAYAT VERİ"),
         str(enj))
    # SINIR: tam toleransta bayrak KAPALI, bir gün ötesinde AÇIK.
    sina("eşik sınırı: tolerans günü kapalı, ertesi gün açık",
         ozet_uret.bayat_karari(tol, [])["bayat"] is False
         and ozet_uret.bayat_karari(tol + 1, [])["bayat"] is True,
         f"tolerans {tol}")
    # YAPISAL KİLİT: karar main()'in içine geri taşınırsa kapı onu koşturamaz.
    sina("bayat kararı ozet_uret.main()'in İÇİNDE değil, ayrı fonksiyonda",
         "bayat_sebep" not in inspect.getsource(ozet_uret.main)
         and "bayat_karari(" in inspect.getsource(ozet_uret.main))


def main() -> int:
    print("KREDİ & PARASAL BÜYÜKLÜKLER — DUMAN SINAMASI")
    gunluk_saat()
    ozet_saatleri()
    bayat_bayragi()
    print(f"\n{len(GECTI)} geçti · {len(DUSTU)} düştü")
    if DUSTU:
        for d in DUSTU:
            print("  ✗ " + d)
        return 1
    print("DUMAN SINAMASI GEÇTİ.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
