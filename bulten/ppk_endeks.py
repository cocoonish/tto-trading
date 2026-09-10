#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PPK ŞAHİN/GÜVERCİN ENDEKSİ — karar metninin tonunu ölçer ve SINAR.

GİRDİ arşivdir (`bulten/veri/ppk`, `ppk_arsiv.py` indirir), hüküm buradadır.
İkisi bilerek ayrı: girdiyi üreten kod hükmü de kurarsa hükmün yanlışı girdiye
sessizce sızar.

YÖNTEM. Bu metinler ŞABLONLU: 10.09.2026 duyurusunun yedi paragrafından altısı
bir önceki metinle birebir aynı. Öyleyse ton, kelime SAYMAKLA değil hangi
CÜMLENİN durup hangisinin gittiğiyle ölçülür. Endeks, tekrar eden cümle
kalıplarının varlık/yokluk vektörüdür; her kalıbın işareti ve ağırlığı
EĞİTİM döneminden kestirilir, hüküm SINAMA döneminde doğrulanır.

NEDEN SÖZLÜK DEĞİL. Şahin/güvercin kelime listesi (Bennani–Neuenkirch tarzı)
Türkçe için doğrulanmış bir karşılığı olmadığından elle kurulurdu; bu depoda
"ikna edici bir tablo, sınanmamış bir kuraldır" yazılı. Üstelik şablonlu
metinde kelime frekansı neredeyse hiç oynamaz — ayrışan şey cümlelerdir.

NEDEN ELLE KALIP SEÇİLMİYOR. "Adımların büyüklüğü" cümlesinin indirimle
ilişkili olduğunu ÖNCE gördüm, SONRA kural yazsaydım bu örneklem içi uydurma
olurdu. Kalıplar mekanik seçiliyor: yeterince sık geçen her cümle aday, işaret
ve ağırlık yalnız eğitim döneminden.

DOĞRULAMA ZORUNLU VE BAŞARISIZLIK DA BİR SONUÇTUR. Endeks, örneklem DIŞI
dönemde saf bir kıyas ölçütünü (her toplantıda "sabit" demek) geçemezse bunu
yazar; geçemediği hâlde yayımlanan bir endeks, ölçülmemiş bir şeyi ölçülmüş
gibi göstermenin bir biçimidir.

Koşum:  python3 bulten/ppk_endeks.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

BURASI = Path(__file__).resolve().parent
ARSIV = BURASI / "veri" / "ppk"

# EĞİTİM / SINAMA sınırı. 2023 başı seçildi ve gerekçesi VERİDEN: TCMB'nin
# faiz patikası 2023 Haziran'da yön değiştirdi (%8,5 → %15) ve o tarihten
# sonrası bugünkü çerçeveyle aynı rejim. Sınır metne bakılarak değil takvimle
# konuyor — sınırı sonuca göre kaydırmak, sınamayı örneklem içine çevirir.
SINIR = "2023-01-01"

# Bir kalıbın aday olması için EN AZ bu kadar kararda geçmesi gerekir.
# Ölçülmemiş bir seviyeye eşik konmaz: bu sayı bir tahmin değil, "iki gözlemden
# işaret kestirilmez" kısıtının en yumuşak hâli; duyarlılığı raporda basılıyor.
ASGARI_GECIS = 8


def _sade(m: str) -> str:
    """Kıyas için sadeleştirme: küçük harf, işaret ve SAYI kaldırma.

    SAYILAR ÇIKARILIYOR, çünkü aynı cümle her toplantıda başka bir oranla
    geçiyor ("yüzde 37'de sabit tutulmasına" · "yüzde 42,5'ten yüzde 46'ya").
    Sayı bırakılsa her cümle tekil görünür ve hiçbir kalıp tekrar etmez —
    yani endeks tanımı gereği hiçbir şey ölçemezdi.
    """
    m = unicodedata.normalize("NFKC", m).lower()
    m = re.sub(r"\d+(?:[.,]\d+)?", "#", m)
    m = re.sub(r"[^\w#\s]", " ", m)
    return re.sub(r"\s+", " ", m).strip()


# DIŞARIDA BIRAKILAN İKİ CÜMLE AİLESİ — ikisi de ölçülerek bulundu.
#
# (1) KURUL ÜYESİ LİSTESİ. İlk koşuda endeksin EN GÜVERCİN kalıbı
# ("murat uysal başkan murat çetinkaya ömer duman …", ağırlık −1,18) bir
# İSİM LİSTESİYDİ. Endeks tonu değil BAŞKAN SABİT ETKİSİNİ öğrenmişti:
# "Uysal başkanken faiz iniyordu" doğru bir gözlem ama metnin TONU değil ve
# yeni bir metin hakkında hiçbir şey söylemez. Örneklem içi isabeti şişirir,
# örneklem dışında hiçbir işe yaramaz.
#
# (2) KARARIN KENDİSİ. "…sabit tutulmasına karar vermiştir" cümlesi kararı
# ANLATIR; eşzamanlı hedefte bu, cevabı soruya koymaktır. İlk koşuda ağırlığı
# küçüktü (−0,02) ama küçük olması meşru yapmaz — sızıntı ölçülünce kaldırılır,
# etkisi küçük diye bırakılmaz.
UYE_SATIRI = re.compile(r"(?i)toplant[ıi]ya kat[ıi]lan kurul [üu]yeleri")
KARAR_CUMLESI = re.compile(
    r"(?i)(karar vermi[şs]tir|sabit tutul|indirilmesine|art[ıi]r[ıi]lmas[ıi]na"
    r"|y[üu]kseltilmesine|sabit tutulmas[ıi]na)")


def _cumleler(paragraflar: list[str]) -> set[str]:
    out = set()
    uye_bekliyor = False
    for p in paragraflar:
        if UYE_SATIRI.search(p):
            uye_bekliyor = True          # SONRAKİ paragraf isim listesidir
            continue
        if uye_bekliyor:
            uye_bekliyor = False
            continue
        for c in re.split(r"(?<=[.!?])\s+", p):
            if KARAR_CUMLESI.search(c):
                continue
            s = _sade(c)
            if len(s) > 40:          # künye ve başlık satırlarını dışarıda bırak
                out.add(s)
    return out


def kararlar() -> list[dict]:
    """Arşivdeki TÜRKÇE faiz kararları, tarihe göre; politika faizi çözülmüş."""
    ks = [json.loads(p.read_text(encoding="utf-8"))
          for p in ARSIV.rglob("*-TR.json")]
    ks = [k for k in ks if k["tur"] == "karar" and k["tarih"] and k["politika"] is not None]
    ks.sort(key=lambda k: k["tarih"])
    for i, k in enumerate(ks):
        k["cumleler"] = _cumleler(k["paragraflar"])
        # HEDEF: BU toplantıda alınan kararın kendisi (puan). Metin o kararı
        # ANLATAN metindir, yani eşzamanlı ölçü; "sonraki toplantıyı öngörür
        # mü" ayrı ve daha iddialı bir soru, aşağıda ayrıca sınanıyor.
        k["degisim"] = None if i == 0 else round(k["politika"] - ks[i - 1]["politika"], 4)
        k["sonraki_degisim"] = None
    for i in range(len(ks) - 1):
        ks[i]["sonraki_degisim"] = ks[i + 1]["degisim"]
    return ks


def agirliklar(egitim: list[dict], hedef: str) -> dict[str, float]:
    """Her kalıbın işareti ve ağırlığı — YALNIZ eğitim döneminden.

    Ağırlık, kalıbın geçtiği kararlardaki ortalama faiz değişimi eksi
    geçmediklerindeki ortalama; yani "bu cümle varken faiz ne yapmış".
    """
    tum: dict[str, int] = {}
    for k in egitim:
        for c in k["cumleler"]:
            tum[c] = tum.get(c, 0) + 1
    w = {}
    for c, n in tum.items():
        if n < ASGARI_GECIS or n > len(egitim) - ASGARI_GECIS:
            continue          # her metinde geçen kalıp ayırt etmez
        var = [k[hedef] for k in egitim if c in k["cumleler"] and k[hedef] is not None]
        yok = [k[hedef] for k in egitim if c not in k["cumleler"] and k[hedef] is not None]
        if len(var) < ASGARI_GECIS or len(yok) < ASGARI_GECIS:
            continue
        w[c] = sum(var) / len(var) - sum(yok) / len(yok)
    return w


def puan(k: dict, w: dict[str, float]) -> float:
    """Kararın ton puanı: taşıdığı kalıpların ağırlık ortalaması.

    ORTALAMA, toplam değil: metin uzunluğu yıllar içinde değişiyor ve toplam
    puan uzun metni sistematik olarak daha 'şahin' gösterirdi.
    """
    p = [w[c] for c in k["cumleler"] if c in w]
    return sum(p) / len(p) if p else 0.0


def _isaret(x: float) -> int:
    return 0 if abs(x) < 1e-9 else (1 if x > 0 else -1)


def sina(hedef: str = "degisim") -> dict:
    """Endeksi ÖRNEKLEM DIŞI sına ve saf kıyas ölçütüyle karşılaştır.

    KIYAS ÖLÇÜTÜ ŞART. 111 kararın 67'si "sabit"; yani her toplantıda hiçbir
    şey demeden "sabit" diyen bir kural sınama döneminde de yüksek isabet
    tutturur. Bir endeksin işe yaradığı ancak O ORANI geçtiğinde söylenebilir.
    """
    ks = kararlar()
    ks = [k for k in ks if k[hedef] is not None]
    egitim = [k for k in ks if k["tarih"] < SINIR]
    sinama = [k for k in ks if k["tarih"] >= SINIR]
    w = agirliklar(egitim, hedef)

    # ÜÇ HÂLLİ SINIFLANDIRMA — ENDEKS "SABİT" DİYEBİLMELİ.
    #
    # İlk yazımda tek eşik vardı ve endeks yapısal olarak hiç "sabit"
    # diyemiyordu (puan eşiğe tam eşit çıkmaz), yani 111 kararın 67'sini
    # TANIMI GEREĞİ ıskalıyordu — eğitim isabeti %30,6, saf kuralın (%66,7)
    # yarısından az. Ölçüt endeksin sinyalini değil kendi kusurunu ölçüyordu.
    # Üç hâl iki eşik ister ve ikisi de EĞİTİMDEN geliyor: bant genişliği,
    # eğitim döneminde "sabit" kararların payını tutturacak biçimde seçiliyor.
    e_puan = sorted(puan(k, w) for k in egitim)
    sabit_pay = sum(1 for k in egitim if abs(k[hedef]) < 1e-9) / len(egitim)
    orta = e_puan[len(e_puan) // 2]
    sapma = sorted(abs(p - orta) for p in e_puan)
    bant = sapma[min(int(sabit_pay * len(sapma)), len(sapma) - 1)]

    def hukum(p: float) -> int:
        if abs(p - orta) <= bant:
            return 0
        return 1 if p > orta else -1

    def isabet(kume):
        if not kume:
            return None, 0
        d = sum(1 for k in kume
                if _isaret(k[hedef]) == hukum(puan(k, w))) / len(kume)
        return d, len(kume)

    esik = orta

    # SAF KIYAS: her toplantıda "değişim yok" de.
    def sabit_kural(kume):
        if not kume:
            return None
        return sum(1 for k in kume if abs(k[hedef]) < 1e-9) / len(kume)

    i_e, n_e = isabet(egitim)
    i_s, n_s = isabet(sinama)
    return {
        "hedef": hedef, "kalip": len(w),
        "egitim_n": n_e, "egitim_isabet": i_e,
        "sinama_n": n_s, "sinama_isabet": i_s,
        "sabit_kural_egitim": sabit_kural(egitim),
        "sabit_kural_sinama": sabit_kural(sinama),
        "esik": esik, "bant": bant,
        "agirliklar": sorted(w.items(), key=lambda kv: kv[1]),
        "sinama_puanlari": [(k["tarih"], round(puan(k, w), 4), k[hedef]) for k in sinama],
    }


def main() -> int:
    ks = kararlar()
    print("PPK ŞAHİN/GÜVERCİN ENDEKSİ")
    print("=" * 74)
    print(f"örneklem: {len(ks)} karar · {ks[0]['tarih']} → {ks[-1]['tarih']}")
    deg = [k for k in ks if k["degisim"] is not None]
    print(f"faiz değişikliği {sum(1 for k in deg if abs(k['degisim'])>1e-9)} · "
          f"sabit {sum(1 for k in deg if abs(k['degisim'])<=1e-9)}")

    for hedef, ad in (("degisim", "EŞZAMANLI (bu toplantının kararı)"),
                      ("sonraki_degisim", "ÖNCÜ (bir sonraki toplantının kararı)")):
        r = sina(hedef)
        print(f"\n▶ {ad}")
        print(f"  seçilen kalıp: {r['kalip']}")
        print(f"  eğitim (<{SINIR}) n={r['egitim_n']:3}  isabet %{100*r['egitim_isabet']:.1f}"
              f"   · saf 'sabit' kuralı %{100*r['sabit_kural_egitim']:.1f}")
        if r["sinama_n"]:
            fark = 100 * (r["sinama_isabet"] - r["sabit_kural_sinama"])
            print(f"  SINAMA (≥{SINIR}) n={r['sinama_n']:3}  isabet %{100*r['sinama_isabet']:.1f}"
                  f"   · saf 'sabit' kuralı %{100*r['sabit_kural_sinama']:.1f}"
                  f"   → fark {fark:+.1f} puan")
            print(f"  HÜKÜM: {'kıyas ölçütünü GEÇİYOR' if fark > 0 else 'kıyas ölçütünü GEÇEMİYOR'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
