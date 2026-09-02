#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — rejim panosu: "neredeyiz" sorusunun dokuz satırlık cevabı.

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
    tarih: str = ""               # girdilerin günü — farklıysa hepsi ('31.08.2026/07.2026')
    ondalik: int = 2              # deger kaç haneyle yuvarlandı (revizyon toleransı)


import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "ortak"))
from bicim import sayi as _sayi, yuzde as _yuzde  # noqa: E402  — sayı yazımı TEK yerden


def redk_konum(sapma10) -> str:
    """REDK'in on yıllık ortalamaya göre yeri — yön işaretten okunur.

    Sapma eksiye döndüğü gün "%−3,2 üstünde" yazılmasın: büyüklük mutlak,
    yön sözcükle ("altında"). Sapma yoksa boş."""
    if sapma10 is None:
        return ""
    yon = "üstünde" if sapma10 >= 0 else "altında"
    return f"on yıllık ortalamanın {_yuzde(abs(sapma10), 1)} {yon}"

def _al(hat: str, *anahtarlar):
    d = gozlem.anlik(hat) or {}
    out = []
    for a in anahtarlar:
        v = d.get(a)
        out.append(float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None)
    return out if len(out) > 1 else out[0]


def _gun(hat: str, *anahtarlar, acik: str = "") -> str:
    """Anahtarların kendi günü (gozlem sözleşmesi: açık alan → <anahtar>_tarih →
    hattın saati). Gösterge şeridiyle AYNI alan geçilmeli — ör. tcmb-net-rezerv
    haftalık serileri için 'h_tarih' — yoksa aynı sayı iki yerde iki tarih taşır."""
    d = gozlem.anlik(hat) or {}
    gunler = []
    for a in anahtarlar:
        t = gozlem.anahtar_tarihi(d, a, acik) if d else ""
        if t and t != "?" and t not in gunler:
            gunler.append(t)
    return "/".join(gunler)


def _gunler(*parcalar: str) -> str:
    """Birden çok hattın günlerini tek anahtarda birleştir (yinelenenler düşer)."""
    out: list[str] = []
    for p in parcalar:
        for g in p.split("/"):
            if g and g not in out:
                out.append(g)
    return "/".join(out)


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
    prim2y, basabas2y, anket2y = _al("tufex-basabas", "prim_2y", "basabas_2y", "anket_2y")
    ayrisma, = [_al("makroihtiyati", "ayrisma")]

    # Girdilerin günleri — satırın revizyon anahtarı (aynı güne ait sayı kıyaslanır).
    g_politika = _gun("fonlama-likidite", "politika")
    g_tufe12, g_bek12 = _gun("enflasyon", "tufe_12a"), _gun("enflasyon", "bek_12a")
    g_d1a = _gun("usdtry-deval", "d1a")
    g_kredi = _gun("kredi-parasal", "g_ar_13y")
    g_redk = _gun("try-reer", "redk")
    g_egim = _gun("dibs-verim-egrisi", "egim_2y9y")
    g_rezerv = _gun("tcmb-net-rezerv", "h_brut", "h_swap_haric", acik="h_tarih")   # gösterge şeridiyle aynı alan
    g_prim = _gun("tufex-basabas", "prim_2y")
    g_ayrisma = _gun("makroihtiyati", "ayrisma")

    s: list[Satir] = []

    if politika is not None and bek12 is not None:
        v = politika - bek12
        e, a = _esik(v, 0, "sıkı", "gevşek",
                     "İleriye dönük reel faizin pozitif olması sıkı para politikasının "
                     "asgari şartıdır; negatifse politika faizi beklenen enflasyonu "
                     "karşılamıyor demektir.")
        s.append(Satir("Reel politika faizi (ileriye dönük)", round(v, 2), "puan",
                       "politika faizi − anketin 12 ay sonrası enflasyon beklentisi",
                       e, a, tarih=_gunler(g_politika, g_bek12), ondalik=2))

    if politika is not None and tufe12 is not None:
        v = politika - tufe12
        e, a = _esik(v, 0, "pozitif", "negatif",
                     "Geriye dönük reel faiz gerçekleşmiş enflasyonu kullanır; ileriye "
                     "dönük olandan ayrışması beklentinin gerçekleşmeden kopmasıdır.")
        s.append(Satir("Reel politika faizi (geriye dönük)", round(v, 2), "puan",
                       "politika faizi − yıllık TÜFE", e, a, tarih=_gunler(g_politika, g_tufe12), ondalik=2))

    if politika is not None and d1a is not None:
        v = politika - d1a
        e, a = _esik(v, 0, "taşıma kârlı", "taşıma zararlı",
                     "Hedge'siz TL taşımanın brüt getirisi. Kur hızı faizin üstüne "
                     "çıktığında taşıma zarara döner; bu makasın kapanması TL "
                     "pozisyonlarının en hızlı çözüldüğü andır.")
        s.append(Satir("TL taşıma makası", round(v, 1), "puan",
                       "politika faizi − 1 aylık yıllıklandırılmış devalüasyon hızı",
                       e, a, tarih=_gunler(g_politika, g_d1a), ondalik=1))

    if kredi is not None and tufe12 is not None:
        v = kredi - tufe12
        e, a = _esik(v, 0, "reel genişleme", "reel daralma",
                     "Nominal kredi büyümesi enflasyonun altındaysa kredi stoku reel "
                     "olarak küçülüyor demektir — makroihtiyati sıkılığın asıl ölçüsü.")
        s.append(Satir("Reel kredi büyümesi", round(v, 1), "puan",
                       "kur arındırılmış 13 hafta yıllıklandırılmış kredi büyümesi − yıllık TÜFE",
                       e, a, tarih=_gunler(g_kredi, g_tufe12), ondalik=1))

    if redk is not None:
        e, a = _esik(sapma10, 0, "reel değerli", "reel ucuz",
                     "REDK'in uzun dönem ortalamasının üstünde olması TL'nin reel "
                     "olarak değerli, yani dış dengeye baskı yapan tarafta olduğunu "
                     "söyler.") if sapma10 is not None else ("", "")
        s.append(Satir("Reel efektif kur", round(redk, 1), "endeks",
                       "TÜFE bazlı REDK", e, a,
                       konum=redk_konum(sapma10), tarih=g_redk, ondalik=1))

    if egim is not None:
        e, a = _esik(egim, 0, "normal eğim", "ters eğri",
                     "Kısa vadeli getirinin uzun vadeliyi aşması, piyasanın bugünkü "
                     "sıkılığın kalıcı olmadığını fiyatlaması demektir.")
        s.append(Satir("DİBS eğri eğimi (2y−9y)", round(egim, 2), "puan",
                       "2 yıllık spot getiri − 9 yıllık spot getiri", e, a, tarih=g_egim, ondalik=2))

    # Dezenflasyon güvenilirliği. Panonun geri kalanı politikanın NE KADAR SIKI
    # olduğunu ölçüyor; bu satır piyasanın o sıkılığın SONUCUNA inanıp
    # inanmadığını ölçüyor. İkisi ayrı sorular: reel faiz tarihî yüksekliğinde
    # olabilir ve piyasa hâlâ hedefin tutmayacağını fiyatlıyor olabilir.
    if prim2y is not None:
        e, a = _esik(prim2y, 5, "güven zayıf", "güven yerinde",
                     "Piyasanın anketin üstüne bindirdiği tazminat. Küçük prim "
                     "iki tarafın aynı patikayı gördüğünü, büyük prim piyasanın "
                     "dezenflasyona bedelsiz inanmadığını söyler. 5 puan eşiği "
                     "takdirîdir ve buraya yazıldığı için tartışılabilir.")
        hesap = "2 yıllık TÜFEX başabaş enflasyonu − anketin 2 yıllık beklentisi"
        if basabas2y is not None and anket2y is not None:
            hesap += f" ({_sayi(basabas2y, 2)} − {_sayi(anket2y, 2)})"
        s.append(Satir("Enflasyon risk primi (2y)", round(prim2y, 2), "puan",
                       hesap, e, a, tarih=g_prim, ondalik=2))

    # Makroihtiyati çerçevenin ETKİNLİĞİ. Reel kredi büyümesi toplamın ne
    # yaptığını söyler; bu satır sınırın İÇİNDE kalanla DIŞINA taşan arasındaki
    # farkı söyler. Ayrışma büyürse sıkılık toplamda değil yalnız düzenlenen
    # kalemlerde vardır — kredi frenine basılıyor ama araç yandan kaçıyordur.
    if ayrisma is not None:
        e, a = _esik(ayrisma, 15, "kaçak geniş", "çerçeve tutuyor",
                     "Büyüme sınırına tabi kalemlerle tabi olmayanlar arasındaki "
                     "yıllıklandırılmış büyüme farkı. Fark açıldıkça sıkılık "
                     "toplam kredide değil yalnız düzenlenen kalemlerde kalır. "
                     "15 puan eşiği takdirîdir.")
        s.append(Satir("Makroihtiyati ayrışma", round(ayrisma, 1), "puan",
                       "sınır dışı kalemlerin büyümesi − sınıra tabi kalemlerin büyümesi",
                       e, a, tarih=g_ayrisma, ondalik=1))

    if brut and swap_haric is not None:
        v = 100 * swap_haric / brut
        aciklama = ("Brüt rezervin ne kadarının borçlanılmamış ve swap'a bağlı olmayan "
                    "kısım olduğu — rezervin miktarı değil KALİTESİ.")
        if altin_pay is not None:
            aciklama += f" Brüt rezervin {_yuzde(altin_pay, 1)}'i altın."
        s.append(Satir("Rezerv kalitesi", round(v, 1), "%",
                       "swap hariç net rezerv / brüt rezerv", "", aciklama, tarih=g_rezerv, ondalik=1))

    return [vars(x) for x in s]


if __name__ == "__main__":
    for x in panosu():
        d = "—" if x["deger"] is None else f"{x['deger']:+g}"
        print(f"  {x['ad']:44s} {d:>9s} {x['birim']:6s} {x['etiket']}")
        print(f"      {x['hesap']}")
        if x["konum"]:
            print(f"      konum: {x['konum']}")
