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
  python irfcl_arsiv.py --dogrula       # üç çapraz kıyas: II.2+II.3 ↔ EVDS aylık,
                                        # I.A(4) ↔ TP.AB.C1, I.A(1)+(2)+(3) ↔ TP.AB.C2
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
    # statuscode:200 + mimetype: arşivde 404/302 olarak kalmış ya da PDF
    # OLMAYAN enstantaneler listeye hiç girmesin. Bunlar filtrelenmediğinde
    # taramanın büyük kısmı indirilemeyen adaylara harcanıyor ve her biri
    # üstel geri çekilmeyle dakikalar yiyor (ölçüldü: 124 adayın çoğu 404).
    # collapse=digest: aynı İÇERİĞİN tekrar tekrar arşivlenmiş kopyalarını
    # teke indirir — dosya adı güvenilmez olduğu için ayırt edici olan içerik.
    "filter": [r"urlkey:.*rt20.*tr\.pdf.*", "statuscode:200",
               "mimetype:application/pdf"],
    "collapse": "digest",
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


# Wayback tabanları, DENENME SIRASIYLA. https önce gelir; bazı ağlarda (ör.
# giden 443'ü kısıtlayan ortamlar) yalnız http açık oluyor ve o durumda bütün
# indirmeler sessizce "hatalı enstantane" diye sayılıyordu — tarama saatlerce
# koşup sıfır gözlem üretiyordu. İçerik zaten PDF imzasıyla doğrulandığı ve
# arşivden okuma yapıldığı için http yedeği kabul edilebilir; sıra ASLA ters
# çevrilmez.
WAYBACK_TABANLARI = ("https://web.archive.org", "http://web.archive.org")


def wayback_indir(ts: str, url: str, deneme: int = 4,
                  bekle: float = 2.0) -> bytes:
    """Wayback agresif hız sınırı uyguluyor — üstel geri çekilmeli tekrar dene."""
    son_hata: Exception | None = None
    for i in range(deneme):
        for taban in WAYBACK_TABANLARI:
            try:
                r = requests.get(f"{taban}/web/{ts}id_/{url}", timeout=120)
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


# Gözlem arşivinin şeması. net_rezerv.gozlem_arsivine_ekle ile AYNI olmalı:
# iki dosya da aynı CSV'ye yazar. Geriye uyumlu — eski satırlarda yeni
# sütunlar NaN kalır.
ARSIV_SUTUNLARI = ["ii2_M", "ii3_M", "resmi_rez_M", "doviz_M", "imf_poz_M",
                   "sdr_M", "altin_M", "mn_ons", "kaynak"]

# Kaç yeni gözlemde bir diske yazılsın (bkz. main içindeki gerekçe).
ARA_KAYIT = 5


def gozlem_yukle() -> pd.DataFrame:
    """Diskteki gözlem arşivi (yoksa boş çerçeve); eksik sütunlar eklenir."""
    if not os.path.exists(GOZLEM_CSV):
        return pd.DataFrame(columns=ARSIV_SUTUNLARI,
                            index=pd.DatetimeIndex([], name="tarih"))
    df = pd.read_csv(GOZLEM_CSV, index_col=0, parse_dates=True)
    for c in ARSIV_SUTUNLARI:
        if c not in df.columns:
            df[c] = pd.NA
    df.index.name = "tarih"
    return df


def gozlem_kaydet(df: pd.DataFrame) -> None:
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_csv(GOZLEM_CSV)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dogrula", action="store_true",
                    help="çapraz kıyas: II.2+II.3 ↔ EVDS aylık IRFCL, "
                         "I.A(4) altın ↔ TP.AB.C1, I.A(1)+(2)+(3) ↔ TP.AB.C2")
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
        # parse_weekly_pdf zorunlu kalemler eksikse zaten hata veriyor; burası
        # ikinci savunma. 0.0 varsayılanı KULLANILMAZ: eksik bacağı sıfır sayan
        # bir gözlem çapayı milyarlarca dolar kaydırır ve kalıcı olarak yazılır.
        zorunlu = ("II_2_acik_M", "II_2_fazla_M", "II_3_toplam_M")
        if tarih is None or any(kalem.get(a) is None for a in zorunlu):
            hatali += 1
            print(f"  [atlandı] {ts} tarih ya da II.2/II.3 bacağı okunamadı")
            continue
        # Zaten arşivde olan bir hafta atlanır — AMA yalnız genişletilmiş
        # şemayla (altın miktarı dahil) kaydedilmişse. Eski dar şemayla
        # yazılmış satırlar yeniden okunup zenginleştirilir; altın miktarı
        # (mn_ons) fiyat etkisi hesabının birinci kademe kaynağıdır.
        if (tarih in arsiv.index
                and arsiv.loc[tarih, "kaynak"] == "irfcl_pdf"
                and pd.notna(arsiv.loc[tarih].get("mn_ons"))):
            continue
        ii2 = kalem["II_2_acik_M"] + kalem["II_2_fazla_M"]
        arsiv.loc[tarih, ARSIV_SUTUNLARI] = [
            ii2, kalem["II_3_toplam_M"],
            kalem.get("resmi_rezerv_varliklari_M"),
            kalem.get("I_A1_doviz_M"), kalem.get("I_A2_imf_poz_M"),
            kalem.get("I_A3_sdr_M"), kalem.get("I_A4_altin_M"),
            kalem.get("mn_ons"), "irfcl_pdf",
        ]
        yeni += 1
        print(f"  + {tarih:%Y-%m-%d}  II.2={ii2:>9.0f}  "
              f"II.3={kalem.get('II_3_toplam_M', 0.0):>8.0f}")
        # ARADA KAYDET. islenen_ekle indirmenin hemen ardından çağrılıyor:
        # süreç burada düşerse o enstantaneler "işlendi" damgasını yer ama
        # arşive hiç yazılmaz — bir daha da denenmez, yani sessiz veri kaybı.
        # Yüzlerce enstantanelik bir taramada bu gerçekçi bir senaryo (Wayback
        # hız sınırı, ağ kopması). Her ARA_KAYIT gözlemde bir diske yaz.
        if yeni % ARA_KAYIT == 0:
            gozlem_kaydet(arsiv)

    gozlem_kaydet(arsiv)
    print(f"\nYeni/güncellenen: {yeni} | hatalı enstantane: {hatali}")
    print(f"Arşiv yazıldı: {GOZLEM_CSV}  ({len(arsiv)} gözlem, "
          f"{arsiv.index.min():%Y-%m-%d} → {arsiv.index.max():%Y-%m-%d})")

    if args.dogrula:
        dogrula(arsiv)


def dogrula(arsiv: pd.DataFrame) -> None:
    """Arşivi bağımsız EVDS serileriyle çapraz sınar.

    Üç kıyas yapılır; üçü de aynı büyüklüğü iki AYRI yayından okur, yani
    aradaki fark yuvarlamayı aşarsa ya PDF ayrıştırıcısı ya da seri eşlemesi
    bozulmuş demektir:

      (1) II.2 + II.3           ↔ EVDS aylık IRFCL (TP.DOVVARNC.K14 + K23)
      (2) I.A(4) altın          ↔ EVDS haftalık TP.AB.C1
      (3) I.A (1)+(2)+(3)       ↔ EVDS haftalık TP.AB.C2

    (2) ve (3) net_rezerv.kimlik_denetimi'nde YALNIZ canlı PDF için yapılır;
    burada TÜM arşive uygulanır. Altın kalemi özellikle önemli: brüt rezervin
    kırılımında döviz bacağı artık olarak belirlendiği için C1'deki bir kayma
    doğrudan "döviz rezervi" satırına yazılır.
    """
    from net_rezerv import (CAPRAZ_TOLERANS_M, REZERV_USD_SERIES,  # noqa: E402
                            fetch_grup, fetch_irfcl_aylik)

    if arsiv.empty:
        print("\nArşiv boş — doğrulanacak gözlem yok.")
        return

    print("\n=== (1) II.2 + II.3  ↔  EVDS aylık IRFCL (ay sonu gözlemleri) ===")
    # Aralık ARŞİVDEN türetilir; sabit geniş bir pencere, serinin başlamadığı
    # yıllara gereksiz istek atar.
    aylik = fetch_irfcl_aylik(
        (arsiv.index.min() - pd.Timedelta(days=40)).strftime("%d-%m-%Y"),
        (arsiv.index.max() + pd.Timedelta(days=40)).strftime("%d-%m-%Y"))
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
    else:
        print("  ay sonuna denk gelen gözlem yok.")

    # (2) ve (3): haftalık USD rezerv tablosu.
    t0 = (arsiv.index.min() - pd.Timedelta(days=7)).strftime("%d-%m-%Y")
    t1 = (arsiv.index.max() + pd.Timedelta(days=7)).strftime("%d-%m-%Y")
    rez = fetch_grup(REZERV_USD_SERIES, t0, t1)

    # DİKKAT: TP.AB.C2 = döviz + IMF rezerv pozisyonu + SDR, yani PDF'in
    # (1)+(2)+(3)'ü. Arşivdeki `doviz_M` yalnız (1)'dir; tek başına kıyaslamak
    # her gözlemde ~7,6 milyar USD'lik sahte bir fark üretir (SDR + IMF
    # pozisyonu). Bu yüzden kıyas kolonu değil, TOPLAYICI verilir.
    for baslik, ark_kolonlar, evds_kolon in (
        ("(2) I.A(4) altın      ↔  EVDS haftalık TP.AB.C1",
         ("altin_M",), "altin_M"),
        ("(3) I.A (1)+(2)+(3)   ↔  EVDS haftalık TP.AB.C2",
         ("doviz_M", "imf_poz_M", "sdr_M"), "doviz_M"),
    ):
        print(f"\n=== {baslik} ===")
        if (any(c not in arsiv.columns for c in ark_kolonlar)
                or evds_kolon not in rez.columns):
            print("  kolon yok — atlandı.")
            continue
        farklar, asan = [], 0
        for d, row in arsiv.iterrows():
            bacaklar = [row.get(c) for c in ark_kolonlar]
            if any(pd.isna(v) for v in bacaklar) or d not in rez.index:
                continue
            pdf_deger = sum(float(v) for v in bacaklar)
            evds = rez.loc[d, evds_kolon]
            if pd.isna(evds):
                continue
            fark = float(pdf_deger) - float(evds)
            farklar.append(abs(fark))
            if abs(fark) > CAPRAZ_TOLERANS_M:
                asan += 1
                print(f"  {d:%Y-%m-%d} PDF={float(pdf_deger):>9.0f}  "
                      f"EVDS={float(evds):>9.0f}  fark={fark:>8.0f}  ← TOLERANS DIŞI")
        if farklar:
            print(f"  n={len(farklar)}  ortalama |fark| = "
                  f"{sum(farklar) / len(farklar):.1f} mn USD  "
                  f"maks = {max(farklar):.0f}  toleransı aşan: {asan} "
                  f"(tolerans {CAPRAZ_TOLERANS_M:.0f} mn USD)")
        else:
            print("  kıyaslanabilir gözlem yok (arşivde alt kalem "
                  "okunmamış ya da tarih haftalık tabloya denk gelmiyor).")


if __name__ == "__main__":
    main()
