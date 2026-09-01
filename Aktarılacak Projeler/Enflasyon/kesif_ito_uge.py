# -*- coding: utf-8 -*-
"""İTO'nun DİĞER endeksleri: hangileri EVDS'te var, hangi seriyle, ne kadar geriye?

SORU: "Ücretliler Geçinme Endeksi de bu ay geldi mi? Geldiyse 2024'ten beri
hesabımıza onu da katalım."

Cevap ancak ölçülerek verilir ve üç ayrı şeyi ölçmek gerekiyor:

  (1) İTO'nun ÜGE'si EVDS'te hangi kod(lar)la duruyor ve nereye kadar gidiyor?
      Katalog (depoda önbellekli, 675 grup) dört aday grup gösteriyor:
        bie_itouge85  İstanbul Geçinme Endeksi (Ücretliler)   1987-01 → 2026-07
        bie_ito95     Geçinme Endeksi (Ücretliler)            1996-01 → 2026-07
        bie_ito68     Geçinme Endeksi (Ücretliler) (1968=100) 1978-01 → 2026-07
        bie_itoteuc   Toptan Eşya + Ücretliler (tüm seriler)  1963-01 → 2026-07
      Grubun ADI biliniyor ama SERİ kodları bilinmiyor; serieList istenir.

  (2) TP.FG.IST2.23 GERÇEKTEN ÜGE mi? Bir basın kaydı, İTO'nun temmuz 2026
      için "gıda ve alkolsüz içecekler: aylık %1,30 · yıllık %37,57"
      açıkladığını söylüyor ve bu iki sayı TP.FG.IST2.23'ün temmuz okumasıyla
      BİREBİR tutuyor. Yani ikinci seri ÜGE değil, tüketici endeksinin GIDA
      alt grubu olabilir. İki sayının tutması güçlü bir iz ama kanıt değil:
      aynı kıyas birkaç ay daha yapılmalı. Bu betik seriyi çeker ve aylık
      değişimlerini basar; kıyas notlanmış sayılarla yapılır.

  (3) Uzun ÜGE serisinin 2024-01 sonrası aylık değişimleri neler? Karşılaştırma
      ancak bu okumalarla kurulabilir. Baz yılı farklı (1995=100 / 1985=100)
      ama AYLIK DEĞİŞİM baza duyarsızdır — üç seriyi aynı grafiğe koyabilmemizin
      sebebi bu, seviyeleri değil değişimleri kıyaslıyoruz.

Koşum:  veri.yml → kesif girdisi (contents: read, tazeleme koşmaz)
"""
from __future__ import annotations

import sys

import veri

print = __import__("functools").partial(print, flush=True)   # noqa: A001

GRUPLAR = ("bie_itouge2023", "bie_itouge85", "bie_ito95", "bie_ito68",
           "bie_itotefe", "bie_itoteuc")


def _dene(etiket: str, url: str, kes: int = 900):
    try:
        v = veri._cek(url, deneme=1)
    except Exception as ex:
        print(f"  {etiket:46s} kapalı ({str(ex)[:70]})")
        return None
    print(f"  {etiket:46s} açık")
    return v


def main() -> int:
    print("▶ 1. GRUPLARIN SERİ LİSTESİ (kod uzayı TAHMİN EDİLMEZ, İSTENİR)")
    kodlar: list[str] = []
    for g in GRUPLAR:
        v = _dene(f"serieList code={g}", f"{veri.BASE}/serieList/type=json&code={g}")
        kayit = v if isinstance(v, list) else ((v or {}).get("items") or [])
        for sr in kayit or []:
            kod = (sr.get("SERIE_CODE") or "").strip()
            print(f"      {kod:18s} {sr.get('START_DATE','')}→{sr.get('END_DATE',''):12s} "
                  f"{sr.get('SERIE_NAME','')}")
            if kod:
                kodlar.append(kod)
    print(f"  toplam seri kodu: {len(kodlar)}")

    # Katalogdan gelmezse elle birkaç aday da yoklanır — ama TAHMİN olduğu
    # açıkça yazılır ve boş dönmesi "yok" demek değildir.
    ADAY = ["TP.FG.IST1.23", "TP.FG.IST2.23", "TP.FG.U95", "TP.FG.U85",
            "TP.FG.T63", "TP.FG.U68"]
    print("\n▶ 2. SERİLERİN KAPSAMI VE SON OKUMALARI")
    for kod in dict.fromkeys(kodlar + ADAY):
        try:
            s = veri.evds_aylik(kod, bas="01-01-2023", yenile=True).dropna()
        except Exception as ex:
            print(f"  {kod:18s} HATA {str(ex)[:60]}")
            continue
        if not len(s):
            print(f"  {kod:18s} boş")
            continue
        a = (s.pct_change() * 100).dropna()
        y = (s.pct_change(12) * 100).dropna()
        print(f"  {kod:18s} n={len(s):3d}  {s.index[0]:%Y-%m}→{s.index[-1]:%Y-%m}  "
              f"son seviye {s.iloc[-1]:.2f}  "
              f"son aylık %{a.iloc[-1]:.2f}  "
              + (f"son yıllık %{y.iloc[-1]:.2f}" if len(y) else "yıllık yok"))
        # 2024-01 sonrası aylık değişimler — karşılaştırma bunlarla kurulacak
        son = a[a.index >= "2024-01-01"]
        if len(son):
            print("      aylık: " + " ".join(
                f"{t:%y-%m}:{v:+.2f}" for t, v in son.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
