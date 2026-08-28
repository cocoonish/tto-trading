# -*- coding: utf-8 -*-
"""TCMB APİ portföyü — analitik bilanço ve haftalık vaziyetten GÜNLÜK iz sürme.

Niçin var
---------
tcmb-api-portfoyu.mdx analizinin ilk sürümü portföyü yalnız HMB'nin haftalık
yatırımcı dağılımından (dibs_tcmb, cuma damgalı) okuyordu. O seri alımların
HAFTASINI söyler, GÜNÜNÜ söylemez; üstelik bir hafta gecikmeyle gelir. TCMB'nin
kendi ihale/kotasyon işlem sayfaları bu çalışma ortamından erişilemez durumda
(ağ vekili tcmb.gov.tr'yi engelliyor) — ama EVDS API'sine GitHub koşucusundan
erişilebiliyor ve analitik bilanço GÜNLÜK yayımlanıyor.

Doğrudan alımlar analitik bilançoda "Hazine Borçları" kaleminin içinde durur:
alım valöründe kalem alış değeri kadar sıçrar. Yani günlük seri, hangi güne
hangi tutarın yerleştiğini stok verisinden bir hafta önce ve gün çözünürlükte
gösterir. İhale duyurusu tutarı nominal, bilanço kaydı alış değeri olduğu için
ikisi kuruşu kuruşuna örtüşmez; iskontolu alımda kayıt nominalin altındadır.

Ne yapar
--------
1) bie_abanlbil (analitik bilanço, günlük) ve bie_mbblnch (haftalık vaziyet)
   gruplarının seri listelerini çeker, data/ altına ham hâliyle koyar ve
   koşu loguna kod|ad çiftlerini basar (hangi kalem hangi kodda — keşif).
2) Analitik bilançonun TÜM serilerini 01.12.2025'ten bugüne günlük çeker →
   data/abanlbil_gunluk.csv. (Grup ~30 seri; tek pencere ~270 gün, sınır yok.)
3) Vaziyetin menkul kıymet/DİBS kalemlerini aynı pencerede çeker →
   data/vaziyet_menkul.csv.
4) Loga son 30 günün "Hazine Borçları" görünümünü basar ki koşu logu tek
   başına da okunabilir olsun.

Anahtar, veri hatlarıyla aynı gelenekle TTO_EVDS_KEY'den okunur ve `key:`
HTTP BAŞLIĞINDA gider (sorgu dizesinde değil — bkz. Butce/veri.py notu).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.request

BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
BURASI = pathlib.Path(__file__).resolve().parent
VERI = BURASI / "data"
VERI.mkdir(exist_ok=True)

BAS = dt.date(2025, 12, 1)          # 2026 turunun öncesinden başla ki sıfır noktası görünsün
SON = dt.date.today()
DEMET = 6                            # Butce/veri.py ile aynı: tek istekte 6 seri


def anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if not a:
        sys.exit("TTO_EVDS_KEY tanımlı değil — bu betik EVDS anahtarıyla koşan "
                 "ortamlar (veri iş akışı) için yazıldı.")
    return a


def cek(yol: str, deneme: int = 3):
    url = f"{BASE}/{yol}"
    son_hata: Exception | None = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(
                url, headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:
            son_hata = ex
            if i < deneme - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"EVDS isteği düştü ({yol}): {son_hata}") from son_hata


def seri_listesi(dg: str) -> list[dict]:
    d = cek(f"serieList/type=json&code={dg}")
    kayit = d if isinstance(d, list) else d.get("items", d)
    (VERI / f"serieList_{dg}.json").write_text(
        json.dumps(kayit, ensure_ascii=False), encoding="utf-8")
    return kayit


def seriler_gunluk(kodlar: list[str], bas: dt.date = BAS,
                   son: dt.date = SON) -> dict[str, dict[str, str]]:
    """{tarih: {kod: değer}} — kodlar DEMET'lenerek tek pencerede çekilir."""
    tablo: dict[str, dict[str, str]] = {}
    for i in range(0, len(kodlar), DEMET):
        demet = kodlar[i:i + DEMET]
        u = (f"series={'-'.join(demet)}"
             f"&startDate={bas:%d-%m-%Y}&endDate={son:%d-%m-%Y}&type=json")
        items = cek(u).get("items", [])
        guvenli = [k.replace(".", "_") for k in demet]
        for satir in items:
            t = satir.get("Tarih")
            if not t:
                continue
            hedef = tablo.setdefault(t, {})
            for kod, g in zip(demet, guvenli):
                hedef[kod] = satir.get(g)
        time.sleep(0.3)
    return tablo


def csv_yaz(yol: pathlib.Path, tablo: dict[str, dict[str, str]],
            kodlar: list[str]) -> None:
    def sirala(t: str) -> dt.date:      # "28-08-2026" → tarih
        g, a, y = t.split("-")
        return dt.date(int(y), int(a), int(g))

    with yol.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tarih"] + kodlar)
        for t in sorted(tablo, key=sirala):
            w.writerow([f"{sirala(t):%Y-%m-%d}"] +
                       [tablo[t].get(k, "") for k in kodlar])
    print(f"  yazıldı: {yol.relative_to(BURASI.parent.parent)} "
          f"({len(tablo)} satır × {len(kodlar)} seri)")


def main() -> None:
    # -- 1) Seri listeleri: hangi kalem hangi kodda ---------------------------
    gruplar = ["bie_abanlbil", "bie_mbblnch", "bie_mbblnca"]
    listeler: dict[str, list[dict]] = {}
    for dg in gruplar:
        print(f"\n== {dg} seri listesi ==")
        try:
            ham = seri_listesi(dg)
        except Exception as ex:
            print(f"  ! liste alınamadı: {ex}")
            continue
        listeler[dg] = ham
        for s in ham:
            print(f"  {s.get('SERIE_CODE')} | {s.get('SERIE_NAME')}")

    # -- 2) Analitik bilanço: TÜM seriler, günlük -----------------------------
    ab = listeler.get("bie_abanlbil", [])
    ab_kodlar = [s["SERIE_CODE"] for s in ab if s.get("SERIE_CODE")]
    if ab_kodlar:
        print(f"\n== analitik bilanço {BAS} → {SON} ({len(ab_kodlar)} seri) ==")
        tablo = seriler_gunluk(ab_kodlar)
        csv_yaz(VERI / "abanlbil_gunluk.csv", tablo, ab_kodlar)

        # Loga özet: adı Hazine/menkul içeren kalemlerin son 30 günü.
        ilginc = [s["SERIE_CODE"] for s in ab
                  if re.search(r"(?i)hazine|menkul|senet", s.get("SERIE_NAME") or "")]
        if ilginc:
            print(f"\n-- son 30 gün ({', '.join(ilginc)}) --")
            def sirala(t: str) -> dt.date:
                g, a, y = t.split("-")
                return dt.date(int(y), int(a), int(g))
            for t in sorted(tablo, key=sirala)[-30:]:
                degerler = "  ".join(f"{k}={tablo[t].get(k)}" for k in ilginc)
                print(f"  {sirala(t):%Y-%m-%d}  {degerler}")

    # -- 2b) Vaziyet toplamları: bilanço-oranı paydası ------------------------
    # Yazıdaki "bilanço oranı" nominal stok / VAZİYET toplam aktifi ile
    # hesaplanıyor; oran serisini tazelemek için payda gerekli. 12 aylık
    # büyüme de anlatıda olduğundan pencere bir yıl geriden başlar.
    uzun_bas = dt.date(2024, 12, 1)
    toplamlar = ["TP.BL053", "TP.BL054", "TP.BL055", "TP.BL123"]
    print(f"\n== vaziyet toplamları {uzun_bas} → {SON} ==")
    tablo_t = seriler_gunluk(toplamlar, bas=uzun_bas)
    csv_yaz(VERI / "vaziyet_toplam.csv", tablo_t, toplamlar)
    def _sirala(t: str) -> dt.date:
        g, a, y = t.split("-")
        return dt.date(int(y), int(a), int(g))
    for t in sorted(tablo_t, key=_sirala)[-8:]:
        print(f"  {_sirala(t):%Y-%m-%d}  BL055={tablo_t[t].get('TP.BL055')}")

    # -- 3) Haftalık vaziyet: menkul kıymet kalemleri -------------------------
    vz = listeler.get("bie_mbblnch", [])
    vz_ilginc = [s["SERIE_CODE"] for s in vz
                 if re.search(r"(?i)menkul|senet|dibs|borçlanma",
                              s.get("SERIE_NAME") or "")]
    if vz_ilginc:
        print(f"\n== haftalık vaziyet menkul kalemleri ({len(vz_ilginc)} seri) ==")
        tablo = seriler_gunluk(vz_ilginc)
        csv_yaz(VERI / "vaziyet_menkul.csv", tablo, vz_ilginc)
        def sirala(t: str) -> dt.date:
            g, a, y = t.split("-")
            return dt.date(int(y), int(a), int(g))
        for t in sorted(tablo, key=sirala)[-12:]:
            degerler = "  ".join(f"{k}={tablo[t].get(k)}" for k in vz_ilginc)
            print(f"  {sirala(t):%Y-%m-%d}  {degerler}")

    print("\nkeşif bitti.")


if __name__ == "__main__":
    main()
