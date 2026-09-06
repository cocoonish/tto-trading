#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keşif: hpbitablo serilerinin GERÇEK başlangıcı nerede?

NEDEN. Bu hattın en pahalı kusuru yanlış bir tarih DEĞİLDİ: elle yazılmış bir
sabitin ÖLÇÜM sanılmasıydı. Katalogdaki başlangıç çekimin alt sınırıydı ve
kapsam denetiminin ölçütü de aynı sabitti — üç yer birbirini doğruluyor
görünürken hiçbiri ölçmüyordu. İlk keşif koşusu 01.01.2024'ten sormuştu ve
dönen ilk cuma (05.01.2024) katalogda "kaynağın yayımladığı ilk gözlem" diye
durdu. Yirmi iki serinin HEPSİNİN aynı güne yapışması kırpılmış bir tarihçenin
imzasıydı; 2005'ten sorulunca tablonun 28.02.2014'te başladığı ve 653 hafta
taşıdığı görüldü — beş kat.

Sonuç yalnız tarihçeyi uzatmadı, bir HÜKMÜN dayanağını da sınadı. Yapısal sıfır
hükmü ("bu bacak serinin ilk gözleminden beri sıfır") ancak elimizdeki ilk
gözlem serinin ilk gözlemiyse kurulabilir. 653 haftanın 653'ünde sıfır çıkması
hükmü GÜÇLENDİRDİ, ama bu bir şans meselesiydi: aynı sabit ters yöne kaysaydı
yayımlanmış hüküm yanlış olurdu. Kapı bu yüzden künyeye kondu — ölçülmemiş
başlangıç taşıyan seri üzerine hüküm kurulmaz — ve bu koşu o kapıyı açan
ölçümdür.

KAPSAM BİR LİSTEDEN DEĞİL KÜNYEDEN TÜRER. Aday listesi elle tutuluyordu ve
tablo başına birkaç temsilci içeriyordu; sonuç, aynı tablodaki bir serinin
(tüzel kişilerin dolar bacağındaki parite etkisi) hiç sorulmamış olmasıydı ve o
seri baştan sona sıfırdı, yani hükmü taşıyan dört bacaktan biriydi. Bakılmayan
yer geçen sınavla aynı görünür. Liste artık kataloğun kendisinden geliyor:
varsayılan olarak başlangıcı HENÜZ ÖLÇÜLMEMİŞ her seri sorulur.

Depoya hiçbir şey yazmaz; çıktı logdadır. Ölçülen başlangıç künyeye ELLE
taşınır (`bas` ve `bas_kanit`), çünkü bir keşif koşusunun kataloğu kendi
kendine güncellemesi, tam olarak kapatmaya çalıştığımız kusurun otomatik
biçimi olurdu: kimsenin bakmadığı bir sabit, kimsenin bakmadığı bir koşudan.

Koşum:
    python3 -u kesif_bas.py            · başlangıcı ölçülmemiş seriler
    python3 -u kesif_bas.py --hepsi    · ölçülmüşler de dahil (gerileme sınaması)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import pandas as pd  # noqa: E402
import veri  # noqa: E402  (hattın kendi istemcisi — ikinci bir istemci yazılmaz)

# Alt sınır künyeden okunur: keşfin sorduğu sınır ile kanıt alanına yazılan
# sınır AYNI olmalı. İki yerde ayrı yazılsalardı künye, hiç yapılmamış bir
# ölçümün alt sınırını ilan edebilirdi.
ERKEN = veri.KESIF_ALT_SINIR

# Demet başına kaç seri: hattın kendi sözleşmesi. Ayrı bir sayı yazmak,
# keşfin ölçtüğü şeyin üretimdekinden farklı bir yoldan gelmesi olurdu.
DEMET = veri.DEMET


def _adaylar(hepsi: bool) -> list[tuple[str, veri.Seri]]:
    """Sorulacak seriler — künyeden, elle tutulan listeden değil."""
    return [(ad, s) for ad, s in veri.HAFTALIK.items()
            if hepsi or not veri.bas_olculdu(ad)]


def main() -> int:
    hepsi = "--hepsi" in sys.argv
    aday = _adaylar(hepsi)
    print(f"ERKEN BAŞLANGIÇ SORUSU — startDate={ERKEN}")
    print(f"  aday: {len(aday)}/{len(veri.HAFTALIK)} seri "
          + ("(hepsi)" if hepsi else "(başlangıcı henüz ölçülmemiş olanlar)"))
    print("=" * 88)
    son = pd.Timestamp.today().normalize() + pd.Timedelta(days=veri.ILERI_GUN)
    bulgu: list[tuple[str, str, str]] = []
    for i in range(0, len(aday), DEMET):
        grup = aday[i:i + DEMET]
        try:
            # Hattın KENDİ çekicisi kullanılır; ikinci bir istemci yazmak,
            # keşfin ölçtüğü şeyin üretimdekinden farklı olması demektir.
            # Parçalama da hattın sabitinden: 2005'ten bugüne pencere tek
            # parçaya sığmaz ve sığdırmaya çalışmak, kaynağın sessiz
            # kırpmasını keşfin kendi içine taşırdı.
            df = veri._demet_cek([s.kod for _a, s in grup],
                                 pd.Timestamp(ERKEN), son,
                                 veri.PARCA_HAFTA_GUN, bicim_ad="gun")
        except Exception as ex:                        # noqa: BLE001
            for ad, s in grup:
                print(f"{ad:20} {s.kod:22} HATA {type(ex).__name__}: {ex}")
            continue
        for ad, s in grup:
            kol = s.kod.replace(".", "_")
            if df is None or df.empty or kol not in df.columns:
                print(f"{ad:20} {s.kod:22} BOŞ")
                continue
            d = df[kol].dropna()
            if not len(d):
                print(f"{ad:20} {s.kod:22} BOŞ (hepsi eksik)")
                continue
            nz = d[d != 0]
            ilk = d.index.min().date()
            print(f"{ad:20} {s.kod:22} n={len(d):5} "
                  f"ilk={ilk} son={d.index.max().date()} "
                  f"sıfırdışı={len(nz):5} "
                  f"ilk_sıfırdışı={nz.index.min().date() if len(nz) else '—'}")
            if str(ilk) != s.bas:
                bulgu.append((ad, s.bas, str(ilk)))
    print("=" * 88)
    # HÜKÜM ÖLÇÜMDEN KURULUR, ölçüm yokken kurulmaz. Sorgunun alt sınırı ile
    # gelen cevabın AYNI güne düşmesi "seri burada başlıyor" demek değildir;
    # bu koşunun alt sınırı kaynağın verebileceğinden kesinlikle daha eski
    # olduğu için (ve ancak o yüzden) cevap bir ölçümdür.
    if bulgu:
        print("KÜNYE İLE ÖLÇÜM AYRIŞIYOR — künyeye taşınacak:")
        for ad, eski, yeni in bulgu:
            print(f"  {ad:20} {eski} → {yeni}")
    else:
        print("Künyedeki başlangıçlar ölçümle örtüşüyor.")
    print(f"Ölçülen her başlangıç künyeye ELLE yazılır: bas ve "
          f"bas_kanit={ERKEN!r}. Kanıt alanı boş kalan seri üzerine "
          "dayanaksız sıfır hükmü kurulmaz; tanım gereği sıfır bundan "
          "bağımsızdır, dayanağı gözlem değil aritmetiktir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
