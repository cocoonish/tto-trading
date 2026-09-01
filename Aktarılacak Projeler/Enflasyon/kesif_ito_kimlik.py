# -*- coding: utf-8 -*-
"""TP.FG.IST1.23 GERÇEKTEN NE? — seri kimliği keşfi.

NEDEN: Hattımız bu seriyi "İstanbul TÜFE (İTO)" diye etiketliyor. O etiket
KAYNAKTAN GELMİYOR: seri, otuzdan fazla başka seriyle birlikte tek bir
commit'te girdi ve adı EVDS'in kendi meta verisiyle hiç karşılaştırılmadı.
Kullanıcı "gördüğüm İTO rakamları farklı, bu enflasyon değil mi" diye sordu
ve bu soru ancak KAYNAĞA sorularak cevaplanır.

Betik üç yoldan seri adını almaya çalışır ve hiçbirini varsaymaz:
  (1) Veri yanıtının HAM JSON'u — EVDS bazen seri adını yanıtın içine koyar.
  (2) categories → datagroups → serieList zinciri: 154 kategorinin altındaki
      veri gruplarını gezip TP.FG.IST kodlarını İÇEREN grubu bulmak.
  (3) Doğrudan seri meta veri uçları.

Koşum:  veri.yml → kesif girdisi
"""
from __future__ import annotations

import json
import sys

import veri

print = __import__("functools").partial(print, flush=True)   # noqa: A001

KODLAR = ["TP.FG.IST1.23", "TP.FG.IST2.23"]


def _dene(etiket: str, url: str, kes: int = 1200):
    try:
        v = veri._cek(url, deneme=1)
    except Exception as ex:
        print(f"  {etiket:52s} kapalı ({str(ex)[:80]})")
        return None
    m = json.dumps(v, ensure_ascii=False)
    print(f"  {etiket:52s} AÇIK ({len(m)} bayt)")
    print("      " + m[:kes])
    return v


def main() -> int:
    print("İTO seri KİMLİĞİ — EVDS")

    print("\n▶ 1. VERİ YANITININ HAM JSON'U (seri adı içeride mi?)")
    for kod in KODLAR:
        _dene(kod, f"{veri.BASE}/series={kod}&startDate=01-01-2026"
                   f"&endDate=01-03-2026&type=json", kes=1500)

    print("\n▶ 2. KATEGORİ → VERİ GRUBU ZİNCİRİ")
    kat = _dene("categories/type=json", f"{veri.BASE}/categories/type=json", kes=2500)
    kayit = kat if isinstance(kat, list) else ((kat or {}).get("items") or [])
    print(f"  kategori sayısı: {len(kayit)}")
    # Kategori kimliğini hangi alan taşıyor bilmiyoruz; hepsini deneriz.
    kimlikler = []
    for k in kayit:
        for alan in ("CATEGORY_ID", "categoryId", "ID", "id", "CATEGORY_CODE"):
            if k.get(alan) is not None:
                kimlikler.append(str(k[alan]))
                break
    print(f"  kimlik çıkarılabilen: {len(kimlikler)}")

    # Veri grubu ucunun biçimini bilmiyoruz; birkaç kalıp denenir (ilk açılan kazanır).
    KALIP = ["datagroups/mode=2/code={k}/type=json",
             "datagroups/code={k}/type=json",
             "datagroups/categoryId={k}/type=json",
             "datagroup/category={k}/type=json"]
    acik_kalip = None
    for kal in KALIP:
        if not kimlikler:
            break
        v = _dene(kal.format(k=kimlikler[0]),
                  f"{veri.BASE}/" + kal.format(k=kimlikler[0]), kes=800)
        if v:
            acik_kalip = kal
            break
    if not acik_kalip:
        print("  veri grubu ucu açılmadı — 3. yola geçiliyor")
    else:
        print(f"\n  açık kalıp: {acik_kalip} — bütün kategoriler taranıyor")
        bulundu = []
        for i, kid in enumerate(kimlikler):
            try:
                v = veri._cek(f"{veri.BASE}/" + acik_kalip.format(k=kid), deneme=1)
            except Exception:
                continue
            gr = v if isinstance(v, list) else (v.get("items") or [])
            for g in gr:
                metin = json.dumps(g, ensure_ascii=False)
                if "FG.IST" in metin or "IST1" in metin:
                    bulundu.append((kid, g))
        print(f"  TP.FG.IST geçen veri grubu: {len(bulundu)}")
        for kid, g in bulundu[:10]:
            print(f"    kategori {kid}: " + json.dumps(g, ensure_ascii=False)[:400])

    # DEPODA ZATEN VARMIŞ. Bu betiğin ilk sürümü yedi grup kodu TAHMİN etti ve
    # yedisi de boş döndü. Oysa deponun başka bir hattı (ÖdemelerDengesi) EVDS'in
    # BÜTÜN veri gruplarını (675 kayıt) çoktan indirip önbelleğe almış ve içinde
    # "İstanbul Tüketici Fiyat Endeksi" adlı grup duruyordu: bie_itouge2023.
    # Bir kaynağa sormadan önce DEPOYA sormak gerekiyordu — aynı soru başka bir
    # hat tarafından çoktan cevaplanmış olabilir.
    print("\n▶ 2b. ADI DEPODAN BULUNAN GRUPLARIN SERİ LİSTESİ")
    for g in ("bie_itouge2023", "bie_itouge85", "bie_ito95", "bie_itoteuc",
              "bie_itotefe", "bie_ito68"):
        v = _dene(f"serieList code={g}", f"{veri.BASE}/serieList/type=json&code={g}",
                  kes=200)
        kayit = v if isinstance(v, list) else ((v or {}).get("items") or [])
        for sr in kayit or []:
            print(f"      {sr.get('SERIE_CODE',''):16s} "
                  f"{sr.get('START_DATE','')}→{sr.get('END_DATE',''):12s} "
                  f"{sr.get('SERIE_NAME','')}")

    print("\n▶ 3. DOĞRUDAN SERİ META VERİ UÇLARI")
    for uc in ["serieList/type=json&code=bie_fgist1",
               "serieList/type=json&code=TP.FG.IST1",
               "series/type=json&code=TP.FG.IST1.23",
               "serieinfo/type=json&code=TP.FG.IST1.23",
               "seriesList/type=json&code=TP.FG.IST1.23"]:
        _dene(uc, f"{veri.BASE}/{uc}", kes=900)

    print("\n▶ 4. KIYAS — aynı pencerede TÜFE ve İTO adayları")
    for ad, kod in (("TÜFE genel", "TP.TUKFIY2025.GENEL"),
                    ("İTO aday 1", "TP.FG.IST1.23"),
                    ("İTO aday 2", "TP.FG.IST2.23")):
        try:
            s = veri.evds_aylik(kod, bas="01-01-2024", yenile=True).dropna()
            y = (s.pct_change(12) * 100).dropna()
            print(f"  {ad:12s} {kod:22s} son {s.index[-1]:%Y-%m} seviye {s.iloc[-1]:.2f} · "
                  f"12 aylık %{y.iloc[-1]:.2f} · aylık %{(s.pct_change()*100).iloc[-1]:.2f}")
        except Exception as ex:
            print(f"  {ad:12s} {kod:22s} HATA {str(ex)[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
