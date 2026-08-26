#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — rejim panosu: "neredeyiz" sorusunun altı satırlık cevabı.

Gösterge şeridi seviye ve farkı verir: politika faizi %37,00, TÜFE %31,75.
Eksik olan bunların BİRLİKTE ne anlama geldiğidir. Politika faizinin yüksek
olması sıkı para politikası demek değildir; enflasyona ve kur beklentisine göre
nerede durduğu demektir. Bu panonun ürettiği her satır iki ya da üç ölçülen
büyüklüğün FARKIDIR ve o farkın işareti rejimi tarif eder.

İki kural:

  Her satırın hesabı yazılır. Sitenin "her grafiğin hesabı anlatılır" kuralı
  burada da geçerli: formül satırın kendisinde durur, okur nereden geldiğini
  aramaz.

  Uydurma konum yok. "Son on yılın %90'ında" demek için on yıllık tarihçe
  gerekir; bülten deposu 20.08.2026'da başladı. Tarihsel konum yalnız hattın
  KENDİSİ hesaplıyorsa gösterilir (REDK'in on yıllık ortalamadan sapması gibi).
  Geri kalanında rejim etiketi açıkça yazılmış bir EŞİKTEN gelir — eşik
  görünür olduğu sürece okur katılmadığı yerde kendi çizgisini çekebilir.
"""
from __future__ import annotations

from dataclasses import dataclass

import gozlem


@dataclass
class Satir:
    ad: str
    deger: float | None
    birim: str
    hesap: str                    # formülün insan dili
    etiket: str = ""              # rejim adı
    aciklama: str = ""            # etiketi doğuran eşik
    konum: str = ""               # hattın kendi hesapladığı tarihsel konum


def _al(hat: str, *anahtarlar):
    d = gozlem.anlik(hat) or {}
    out = []
    for a in anahtarlar:
        v = d.get(a)
        out.append(float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None)
    return out if len(out) > 1 else out[0]


def _esik(v: float | None, sinir: float, ust: str, alt: str, aciklama: str):
    if v is None:
        return "", ""
    return (ust if v >= sinir else alt), aciklama


def panosu() -> list[dict]:
    politika, = [_al("fonlama-likidite", "politika")]
    tufe12, bek12 = _al("enflasyon", "tufe_12a", "bek_12a")
    d1a, = [_al("usdtry-deval", "d1a")]
    kredi, = [_al("kredi-parasal", "g_ar_13y")]
    redk, sapma10 = _al("try-reer", "redk", "sapma10")
    egim, = [_al("dibs-verim-egrisi", "egim_2y9y")]
    brut, swap_haric, altin_pay = _al("tcmb-net-rezerv", "h_brut", "h_swap_haric", "p_altin_pay")

    s: list[Satir] = []

    if politika is not None and bek12 is not None:
        v = politika - bek12
        e, a = _esik(v, 0, "sıkı", "gevşek",
                     "İleriye dönük reel faizin pozitif olması sıkı para politikasının "
                     "asgari şartıdır; negatifse politika faizi beklenen enflasyonu "
                     "karşılamıyor demektir.")
        s.append(Satir("Reel politika faizi (ileriye dönük)", round(v, 2), "puan",
                       "politika faizi − anketin 12 ay sonrası enflasyon beklentisi",
                       e, a))

    if politika is not None and tufe12 is not None:
        v = politika - tufe12
        e, a = _esik(v, 0, "pozitif", "negatif",
                     "Geriye dönük reel faiz gerçekleşmiş enflasyonu kullanır; ileriye "
                     "dönük olandan ayrışması beklentinin gerçekleşmeden kopmasıdır.")
        s.append(Satir("Reel politika faizi (geriye dönük)", round(v, 2), "puan",
                       "politika faizi − yıllık TÜFE", e, a))

    if politika is not None and d1a is not None:
        v = politika - d1a
        e, a = _esik(v, 0, "taşıma kârlı", "taşıma zararlı",
                     "Hedge'siz TL taşımanın brüt getirisi. Kur hızı faizin üstüne "
                     "çıktığında taşıma zarara döner; bu makasın kapanması TL "
                     "pozisyonlarının en hızlı çözüldüğü andır.")
        s.append(Satir("TL taşıma makası", round(v, 1), "puan",
                       "politika faizi − 1 aylık yıllıklandırılmış devalüasyon hızı",
                       e, a))

    if kredi is not None and tufe12 is not None:
        v = kredi - tufe12
        e, a = _esik(v, 0, "reel genişleme", "reel daralma",
                     "Nominal kredi büyümesi enflasyonun altındaysa kredi stoku reel "
                     "olarak küçülüyor demektir — makroihtiyati sıkılığın asıl ölçüsü.")
        s.append(Satir("Reel kredi büyümesi", round(v, 1), "puan",
                       "kur arındırılmış 13 hafta yıllıklandırılmış kredi büyümesi − yıllık TÜFE",
                       e, a))

    if redk is not None:
        e, a = _esik(sapma10, 0, "reel değerli", "reel ucuz",
                     "REDK'in uzun dönem ortalamasının üstünde olması TL'nin reel "
                     "olarak değerli, yani dış dengeye baskı yapan tarafta olduğunu "
                     "söyler.") if sapma10 is not None else ("", "")
        s.append(Satir("Reel efektif kur", round(redk, 1), "endeks",
                       "TÜFE bazlı REDK", e, a,
                       konum=f"on yıllık ortalamanın %{sapma10:+.1f} üstünde"
                       if sapma10 is not None else ""))

    if egim is not None:
        e, a = _esik(egim, 0, "normal eğim", "ters eğri",
                     "Kısa vadeli getirinin uzun vadeliyi aşması, piyasanın bugünkü "
                     "sıkılığın kalıcı olmadığını fiyatlaması demektir.")
        s.append(Satir("DİBS eğri eğimi (2y−9y)", round(egim, 2), "puan",
                       "2 yıllık spot getiri − 9 yıllık spot getiri", e, a))

    if brut and swap_haric is not None:
        v = 100 * swap_haric / brut
        aciklama = ("Brüt rezervin ne kadarının borçlanılmamış ve swap'a bağlı olmayan "
                    "kısım olduğu — rezervin miktarı değil KALİTESİ.")
        if altin_pay is not None:
            aciklama += f" Brüt rezervin %{altin_pay:.1f}'i altın."
        s.append(Satir("Rezerv kalitesi", round(v, 1), "%",
                       "swap hariç net rezerv / brüt rezerv", "", aciklama))

    return [vars(x) for x in s]


if __name__ == "__main__":
    for x in panosu():
        d = "—" if x["deger"] is None else f"{x['deger']:+g}"
        print(f"  {x['ad']:44s} {d:>9s} {x['birim']:6s} {x['etiket']}")
        print(f"      {x['hesap']}")
        if x["konum"]:
            print(f"      konum: {x['konum']}")
