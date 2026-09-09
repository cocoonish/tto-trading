#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USDTRYDeval — ŞEKİL SAAT DEFTERİ: her figürün bacak uçları TEK fonksiyonda.

NEDEN VAR. Bu hattın figürleri tek ritimde DEĞİL. Şekil 01–03'te üç bacak yan
yana çiziliyor:

  · kur            — Yahoo Finance, her işlem günü;
  · TLREF          — EVDS, her iş günü;
  · banka faizleri — EVDS haftalık (ihtiyaç kredisi + 1/3/6/12 ay mevduat),
                     Cuma tarihli ve ~bir hafta gecikmeli yayımlanıyor.

09.09.2026'da yayımlanmış figürlerden ÖLÇÜLDÜ: kur ve TLREF izleri 08.09.2026'da,
kredi/mevduat izlerinin dördü de 28.08.2026'da bitiyor (kredi serisi 80 haftanın
80'inde Cuma tarihli, kesintisiz 7 günlük ritim). Sayfa ise üç figürü de hattın
TEK ana saatiyle damgalıyordu — yani 11 gün eski bir faiz katmanı "veri
08.09.2026" diye okura gidiyordu. Kusur iki yönde birden yalan söyler: bayat
bacak taze görünür, ve tek damgayı sayfanın tamamına yoran okur TAZE kur
bacağını da bayat sanır.

SÖZLEŞME (CLAUDE.md). Karma bir figürün damgası bağlayıcı bacaktır; bacaklar
birbirinden uzaksa damga PARÇALI yazılır ve her bacak ADIYLA durur. Buradaki
mesafe 11 gün ve iki bacak iki AYRI RİTİMDE, o yüzden parçalı yazım seçildi.
Aynı güne düşen bacaklar tek parçada birleşir ("kur ve TLREF 08.09.2026"), yani
üç bacak aynı gün bittiğinde damga kendiliğinden kısalır.

İKİ TÜKETİCİ, TEK KAYNAK. Şekil saatleri üç ayrı çizim betiğinden ve özet
üreticisinden okunuyor. Elle tutulan iki liste bir gün sessizce ayrışır ve
figürün alt başlığı ile sayfadaki damga farklı gün söyler; bu yüzden hangi
bacağın hangi figürü bağladığı YALNIZ burada yazılı.

Ağa çıkmaz, plotly/pandas istemez: `duman.py` ve özet üreticisi onu doğrudan
çağırabilsin diye saf stdlib.
"""
from __future__ import annotations

import datetime as _dt


def _bicim():
    """ortak/bicim — tarihin TEK yazımı (GG.AA.YYYY). Hat kendi klasöründen elle
    koşturulursa ortak/ PYTHONPATH'te olmayabilir; depo kökünden bulunur."""
    try:
        import bicim
    except ImportError:
        import pathlib as _pl
        import sys as _sys
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


# Siteye kopyalanan figür adları (guncelle.py kütüğündeki HEDEF adlar). Defterin
# anahtarı budur, üretimdeki dosya adı değil: GrafikEmbed `src`in son parçasına
# bakar ve haftalık/aylık figürler siteye başka adla kopyalanıyor.
DEVAL_1Y = "usdtry_deval.html"
DEVAL_3A = "usdtry_deval_3m.html"
DEVAL_6A = "usdtry_deval_6m.html"
SEGMENT = "usdtry_deval_seg.html"
HAFTALIK = "usdtry_weekly.html"
AYLIK = "usdtry_monthly.html"

SEKIL_DOSYALARI = (DEVAL_1Y, DEVAL_3A, DEVAL_6A, SEGMENT, HAFTALIK, AYLIK)

# KARMA figürler: birden çok bacak taşırlar ve damgaları HER ZAMAN etiketlidir
# (tek bacak kalsa bile "kur 08.09.2026" yazılır, çıplak tarihe düşmez).
# Sebebi yapısal: MDX bu figürleri açık `tarihAnahtari` ile çağırıyor; damga bir
# gün çıplak tarihe düşerse `defter_ayir` onu deftere yazar, `damga_…` anahtarı
# hiç üretilmez ve sayfa sınavı 18b "anahtar ozet.json'da yok" der.
KARMA = (DEVAL_1Y, DEVAL_3A, DEVAL_6A)

# Bacak adları okur diline yazılır: dosya, seri kodu ya da anahtar adı değil.
BACAK_KUR = "kur"
BACAK_TLREF = "TLREF"
BACAK_FAIZ = "banka faizi"


def gun_yaz(t) -> str | None:
    """→ "08.09.2026"; çözülemeyen değer None (uydurma yok)."""
    b = _bicim()
    d = b.tarihe_cevir(t)
    return None if d is None else b.tarih_kisa(d)


def _ve(adlar: list[str]) -> str:
    """["kur", "TLREF"] → "kur ve TLREF"."""
    if len(adlar) == 1:
        return adlar[0]
    return ", ".join(adlar[:-1]) + " ve " + adlar[-1]


def damga(uclar) -> str | None:
    """[(bacak adı, tarih), …] → "kur ve TLREF 08.09.2026 · banka faizi 28.08.2026".

    · Ölçülemeyen bacak (None) damgadan DÜŞER: çizilmemiş bir seri için tarih
      yazmak, ölçülmemiş bir günü ilan etmektir.
    · Aynı güne düşen bacaklar tek parçada birleşir; sıra verilen sıradır
      (lejant sırası), tarihe göre değil — okur figürdeki sırayı arar.
    · Hiçbir bacak ölçülemediyse None: sayfa o şeklin altına tarih hiç basmaz.
    """
    var = [(ad, gun_yaz(t)) for ad, t in uclar]
    var = [(ad, g) for ad, g in var if g]
    if not var:
        return None
    parcalar: list[tuple[list[str], str]] = []
    for ad, g in var:
        if parcalar and parcalar[-1][1] == g:
            parcalar[-1][0].append(ad)
        else:
            parcalar.append(([ad], g))
    return " · ".join(f"{_ve(adlar)} {g}" for adlar, g in parcalar)


def sekil_saatleri(kur=None, tlref=None, faiz_hafta=None,
                   hafta_kur=None, ay_kur=None,
                   dosyalar=None) -> dict[str, str | None]:
    """Hangi bacak hangi figürü bağlar — TEK tanım.

    `dosyalar` verilirse yalnız o figürler döner: her çizim betiği KENDİ
    figürlerinin saatini yazar. Sebebi ölçülmüş bir kusur sınıfı: bir betik
    düşerse onun HTML'i eski kalır, ama saatini başka bir betiğin taze
    ölçüsünden yazarsak bayat figür taze damgalanır.

    · Şekil 01–03 (1 yıl / 3 ay / 6 ay): deval eğrileri + TLREF + haftalık banka
      faizleri. Figürün SÖZÜ bu serilerin kıyasıdır, o yüzden damga parçalı.
    · Şekil 04 (segment kanalları), 05 (haftalık), 06 (aylık): yalnız kurdan
      türer; tek bacak, çıplak tarih.
    """
    karma = damga([(BACAK_KUR, kur), (BACAK_TLREF, tlref),
                   (BACAK_FAIZ, faiz_hafta)])
    tumu: dict[str, str | None] = {
        DEVAL_1Y: karma,
        DEVAL_3A: karma,
        DEVAL_6A: karma,
        SEGMENT: gun_yaz(kur),
        HAFTALIK: gun_yaz(kur if hafta_kur is None else hafta_kur),
        AYLIK: gun_yaz(kur if ay_kur is None else ay_kur),
    }
    if dosyalar is None:
        return tumu
    return {d: tumu[d] for d in dosyalar}


def defter_ayir(saatler: dict[str, str | None]) -> tuple[dict, dict]:
    """Şekil saatlerini İKİ tüketiciye MEKANİK olarak dağıtır → (defter, birleşik).

    · defter   → ozet.json `_sekil_tarih`; TEK tarih ya da None. Parçalı damga
      buraya YAZILAMAZ: sayfa sınavı 18 çözemediği değeri ENGEL sayar.
    · birleşik → `damga_<figür kökü>`; MDX bunları `tarihAnahtari` ile çağırır ve
      sayfa sınavı 18b içlerindeki her tarihi ayrı ayrı sınar.

    Ayrım BURADA yapılır. İki liste elle tutulsaydı bir gün ayrışır ve aynı
    figür için defterle açık anahtar farklı gün söylerdi (sayfa sınavı 18c).
    """
    b = _bicim()
    defter: dict[str, str | None] = {}
    birlesik: dict[str, str] = {}
    for dosya, deger in saatler.items():
        if deger and b.tarihe_cevir(deger) is None:
            defter[dosya] = None
            birlesik["damga_" + dosya.split(".")[0]] = deger
        else:
            defter[dosya] = deger
    return defter, birlesik


def kayit(saatler: dict[str, str | None], **ek) -> dict:
    """Çizim betiğinin yan dosyasına yazılacak kayıt: defter + parçalı damgalar
    + betiğin ilan ettiği bacak saatleri (`tlref_tarih` gibi)."""
    defter, birlesik = defter_ayir(saatler)
    d: dict = {"_sekil_tarih": defter}
    d.update(birlesik)
    d.update(ek)
    return d


def seri_sonu(s) -> _dt.date | None:
    """Bir pandas serisinin son gözlem günü; seri yok ya da boşsa None.

    "Çekilemedi" ile "boş döndü" arasında fark yok: ikisi de ÖLÇÜLEMEDİ demek
    ve ikisinde de bacak damgadan düşer."""
    try:
        if s is None or len(s) == 0:
            return None
        return s.index[-1].date()
    except Exception:                                          # noqa: BLE001
        return None


def bacak_saati(*seriler) -> _dt.date | None:
    """Aynı yayımdan gelen serilerin BAĞLAYICI (en eski) ucu; hiçbiri yoksa None.

    Haftalık banka faizi bacağı beş seriden oluşuyor (ihtiyaç kredisi + dört
    mevduat vadesi). Biri geride kalırsa figürün o katmanı orada biter; en
    tazesini yazmak öbür dördünü olduğundan yeni gösterir."""
    uclar = [g for g in (seri_sonu(s) for s in seriler) if g is not None]
    return min(uclar) if uclar else None


# ---------------------------------------------------------------- yan dosyalar
# Çizim betiklerinin yazdığı ve `ozet_uret.py`nin özete kattığı dosyalar.
YAN_DOSYALAR = ("istatistik_seg.json", "istatistik_hafta.json",
                "istatistik_ay.json", "istatistik_sekil.json")


def yan_dosyalari_birlestir(o: dict, base: str, uyar=print) -> dict:
    """Yan dosyaları `o`ya katar; `_sekil_tarih` sözlüğünü EZMEZ, BİRLEŞTİRİR.

    Şekil saat defterini üç ayrı betik yazıyor (deval figürleri, haftalık, aylık)
    ve her biri yalnız KENDİ figürlerinin girdisini taşıyor. Düz bir `update`
    sonuncunun sözlüğünü geçerli kılar, öbür beş figür defterden düşer ve sayfa
    sınavının 18. ölçütü onları "girdisi olmayan figür" diye sayar — yani
    figürler yine hattın tek ana saatiyle damgalanır ve düzeltmenin tamamı boşa
    gider. Kusur sessizdir: dosya var, okunur, hata vermez.

    Ağa çıkmaz; `duman.py` bunu kendi kurduğu geçici klasörle sınayabilsin diye
    özet üreticisinin İÇİNDE değil BURADA duruyor.
    """
    import json
    import os
    for ad in YAN_DOSYALAR:
        yol = os.path.join(base, ad)
        if not os.path.exists(yol):
            continue
        try:
            y = json.load(open(yol, encoding="utf-8"))
        except Exception as e:                                 # noqa: BLE001
            uyar(f"{ad} okunamadı: {e}")
            continue
        defter = y.pop("_sekil_tarih", None)
        if isinstance(defter, dict):
            o.setdefault("_sekil_tarih", {}).update(defter)
        o.update(y)
    return o



if __name__ == "__main__":                                     # elle bakmak için
    import json
    print(json.dumps(kayit(sekil_saatleri(kur="2026-09-08", tlref="2026-09-08",
                                          faiz_hafta="2026-08-28")),
                     ensure_ascii=False, indent=1))
