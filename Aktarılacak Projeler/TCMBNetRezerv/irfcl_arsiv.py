"""IRFCL haftalık gözlem arşivi (irfcl_gozlem.csv) — tek seferlik / seyrek backfill.

Neden var:
  TCMB'nin "Uluslararası Rezervler ve Döviz Likiditesi" (IRFCL) HAFTALIK tablosu
  sitede yalnızca EN SON hafta için duruyor; geçmiş haftalar için ne arşiv sayfası
  ne de tarihten üretilebilen bir URL var (dosya adı ne verilirse verilsin sunucu
  hep güncel PDF'i döndürüyor -- doğrulandı). Bu yüzden II.2/II.3 kalemlerinin
  GERÇEK geçmişi iki kaynaktan toplanıyor:

    1. EVDS AYLIK IRFCL serileri (TP.DOVVARNC.K14 = II.2 toplam,
       TP.DOVVARNC.K23 = II.3 toplam) — 2000-08'den bugüne, ay sonu.
       Bunlar net_rezerv.py içinde doğrudan EVDS'ten çekiliyor, burada değil.
    2. Wayback Machine'de kalmış haftalık RT*.pdf enstantaneleri — ay içi
       (ara hafta) gözlemleri. Bu script onları toplar.

  DİKKAT: Wayback'teki dosya ADI güvenilmez (sunucu eski dosya adına da güncel
  PDF'i döndürdüğü için arşiv eski URL'yi geç tarihte tekrar taradığında içerik
  başka bir haftaya ait olabiliyor). Bu yüzden tarih HER ZAMAN PDF'in İÇİNDEN
  okunuyor; dosya adı sadece aday listesi için kullanılıyor.

Kullanım:
  python irfcl_arsiv.py                 # Wayback'i tara, irfcl_gozlem.csv'yi güncelle
  python irfcl_arsiv.py --dogrula       # EVDS aylık ile ay sonu gözlemleri karşılaştır
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

import pandas as pd
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
GOZLEM_CSV = os.path.join(BASE, "irfcl_gozlem.csv")
ISLENEN_TXT = os.path.join(BASE, "irfcl_arsiv_islenen.txt")

CDX_URL = "http://web.archive.org/cdx/search/cdx"
CDX_PARAMS = {
    "url": "tcmb.gov.tr/wps/wcm/connect/*",
    "matchType": "domain",
    "filter": r"urlkey:.*rt20.*tr\.pdf.*",
    "output": "text",
    "fl": "timestamp,original",
}


def wayback_adaylari() -> list[tuple[str, str]]:
    """(timestamp, url) listesi — eskiden yeniye."""
    r = requests.get(CDX_URL, params=CDX_PARAMS, timeout=180)
    r.raise_for_status()
    out: list[tuple[str, str]] = []
    for ln in r.text.strip().split("\n"):
        parts = ln.split()
        if len(parts) < 2:
            continue
        if re.search(r"/RT\d{8}TR\.pdf", parts[1], re.I):
            out.append((parts[0], parts[1]))
    return sorted(set(out))


def wayback_indir(ts: str, url: str, deneme: int = 4,
                  bekle: float = 2.0) -> bytes:
    """Wayback agresif hız sınırı uyguluyor — üstel geri çekilmeli tekrar dene."""
    son_hata: Exception | None = None
    for i in range(deneme):
        try:
            r = requests.get(f"https://web.archive.org/web/{ts}id_/{url}",
                             timeout=120)
            if r.status_code == 200 and r.content[:5] == b"%PDF-":
                return r.content
            son_hata = RuntimeError(f"HTTP {r.status_code}")
        except Exception as exc:
            son_hata = exc
        time.sleep(bekle * (2 ** i))
    raise son_hata or RuntimeError("indirilemedi")


def islenen_yukle() -> set[str]:
    if not os.path.exists(ISLENEN_TXT):
        return set()
    with open(ISLENEN_TXT) as f:
        return {ln.strip() for ln in f if ln.strip()}


def islenen_ekle(ts: str) -> None:
    with open(ISLENEN_TXT, "a") as f:
        f.write(ts + "\n")


def gozlem_yukle() -> pd.DataFrame:
    """Diskteki gözlem arşivi (yoksa boş çerçeve)."""
    cols = ["ii2_M", "ii3_M", "kaynak"]
    if not os.path.exists(GOZLEM_CSV):
        return pd.DataFrame(columns=cols, index=pd.DatetimeIndex([], name="tarih"))
    df = pd.read_csv(GOZLEM_CSV, index_col=0, parse_dates=True)
    df.index.name = "tarih"
    return df


def gozlem_kaydet(df: pd.DataFrame) -> None:
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_csv(GOZLEM_CSV)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dogrula", action="store_true",
                    help="EVDS aylık IRFCL ile ay sonu gözlemleri kıyasla")
    ap.add_argument("--limit", type=int, default=0,
                    help="en fazla kaç enstantane indirilsin (0 = hepsi)")
    ap.add_argument("--bekle", type=float, default=1.5,
                    help="enstantaneler arası bekleme (sn) — Wayback hız sınırı")
    args = ap.parse_args()

    sys.path.insert(0, BASE)
    from net_rezerv import parse_weekly_pdf  # noqa: E402

    arsiv = gozlem_yukle()
    print(f"Mevcut arşiv: {len(arsiv)} gözlem")

    adaylar = wayback_adaylari()
    islenen = islenen_yukle()
    adaylar = [(ts, u) for ts, u in adaylar if ts not in islenen]
    print(f"Wayback enstantanesi (işlenmemiş): {len(adaylar)}")
    if args.limit:
        adaylar = adaylar[: args.limit]

    yeni, hatali = 0, 0
    for ts, url in adaylar:
        try:  # indirme: başarısızsa kalıcı işaretleme yok (sonraki koşu dener)
            pdf = wayback_indir(ts, url, bekle=args.bekle)
        except Exception as exc:
            hatali += 1
            print(f"  [atlandı-indirme] {ts} {type(exc).__name__}")
            continue
        finally:
            time.sleep(args.bekle)
        islenen_ekle(ts)  # indirildi → bir daha çekme
        try:
            kalem = parse_weekly_pdf(pdf)
        except Exception as exc:  # bozuk/okunamayan enstantane
            hatali += 1
            print(f"  [atlandı-ayrıştırma] {ts} {type(exc).__name__}")
            continue
        tarih = kalem.get("tarih")
        if tarih is None or "II_2_acik_M" not in kalem:
            hatali += 1
            print(f"  [atlandı] {ts} tarih/II.2 okunamadı")
            continue
        if tarih in arsiv.index and arsiv.loc[tarih, "kaynak"] == "irfcl_pdf":
            continue
        ii2 = kalem.get("II_2_acik_M", 0.0) + kalem.get("II_2_fazla_M", 0.0)
        arsiv.loc[tarih, ["ii2_M", "ii3_M", "kaynak"]] = [
            ii2, kalem.get("II_3_toplam_M", 0.0), "irfcl_pdf",
        ]
        yeni += 1
        print(f"  + {tarih:%Y-%m-%d}  II.2={ii2:>9.0f}  "
              f"II.3={kalem.get('II_3_toplam_M', 0.0):>8.0f}")

    gozlem_kaydet(arsiv)
    print(f"\nYeni/güncellenen: {yeni} | hatalı enstantane: {hatali}")
    print(f"Arşiv yazıldı: {GOZLEM_CSV}  ({len(arsiv)} gözlem, "
          f"{arsiv.index.min():%Y-%m-%d} → {arsiv.index.max():%Y-%m-%d})")

    if args.dogrula:
        from net_rezerv import fetch_irfcl_aylik  # noqa: E402
        aylik = fetch_irfcl_aylik("01-01-2000", "31-12-2030")
        ort = []
        for d, row in arsiv.iterrows():
            # ay sonu gözlemi mi? (aynı ayın son EVDS gözlemiyle kıyasla)
            ay_sonu = d + pd.offsets.MonthEnd(0)
            if (ay_sonu - d).days > 3 or ay_sonu not in aylik.index:
                continue
            fark = (row["ii2_M"] + row["ii3_M"]) - aylik.loc[ay_sonu, "toplam_M"]
            ort.append(abs(fark))
            print(f"  {d:%Y-%m-%d} PDF={row['ii2_M'] + row['ii3_M']:>9.0f}  "
                  f"EVDS={aylik.loc[ay_sonu, 'toplam_M']:>9.0f}  fark={fark:>8.0f}")
        if ort:
            print(f"  ortalama |fark| = {sum(ort) / len(ort):.1f} milyon USD "
                  f"({len(ort)} ay sonu gözlemi)")


if __name__ == "__main__":
    main()
