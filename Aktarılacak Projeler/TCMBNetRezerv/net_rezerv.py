"""TCMB Net Uluslararası Rezerv Hesaplama Scripti.

Hesaplama yöntemi (Bloomberg / Mahfi Eğilmez / Paraanaliz uyumu):

  Net Rezerv (USD)  = TP.AB.N06 (Stand-By Cari "2A Net Uluslararası Rezervler",
                      Bin TL) / TP.DK.USD.A.YTL  (Cuma kapanışı)

  Swap Hariç Net Rezerv (T) = Net Rezerv (T) + swap_düzeltme (T)
                      swap_düzeltme = II.2 + II.3  (IRFCL, negatif)
                      ‣ II.2 = "Yurt İçi Para Karşılığında Döviz Forward ve
                        Future toplam açık+fazla pozisyon" (para swaplarının
                        gelecekteki bacağını da kapsar)
                      ‣ II.3 = "Diğer" (repo/ticari/diğer borç-alacak net)

  swap_düzeltme SERİSİ (kritik): tarihe göre değişir, sabit değil.
  Gerçek gözlem kaynakları:
    1. EVDS AYLIK IRFCL: TP.DOVVARNC.K14 (II.2) + TP.DOVVARNC.K23 (II.3),
       2000-08'den bugüne, ay sonu. Ay sonu tarihlerinde haftalık PDF ile
       milyon USD hassasiyetinde birebir aynı (doğrulandı).
    2. irfcl_gozlem.csv: ay içi HAFTALIK IRFCL gözlemleri (irfcl_arsiv.py ile
       Wayback'ten toplanan + her koşuda eklenen canlı PDF noktası).
  Gözlem olmayan günler iki gerçek gözlem arasında zamana göre ara değerle
  doldurulur; ilk gözlemden önce ve son gözlemden 3 haftadan fazla sonra NaN
  bırakılır. Tek bir güncel sabitin geçmişe yayılması YAPILMAZ.

Günlük tahmin (Cuma anchor + analitik bilanço delta):

  Net Rezerv (T)      = (TP.AB.N06_son_Cuma + ΔAnalitik_TL(son_Cuma→T))
                        / TP.DK.USD.A.YTL(T)
                        ΔAnalitik = Δ(TP.AB.A02 - TP.AB.A14)
                        A02 = Dış Varlıklar, A14 = Bankaların Döviz Mevduatı
                        (analitik bilanço, iş günü)

  Neden A14: Stand-By net rezervin (N06 = N07 - N08) yükümlülük tarafında
  ağırlık bankaların döviz mevduatıdır (N09; IMF ve "diğer" hafta içinde
  neredeyse sabit). Analitik bilançoda aynı kalem A14 olarak HER İŞ GÜNÜ
  gelir; Cuma günleri N09 ile bin TL hassasiyetinde aynıdır (07.08.2026:
  ikisi de 4.799.989). Eskiden A17 çıkarılıyordu — A17 EMİSYON'dur, döviz
  yükümlülüğü değil (A16 Rezerv Para = A17 + A18 + A21 + A22 eşitliği bunu
  gösterir). Emisyon dalgalanması sinyale karışıyor, banka mevduatındaki
  hareket ise hiç görülmüyordu: brüt artıp net sabit kaldığında günlük tahmin
  haftayı 4-5 milyar USD yukarıda bitirip Cuma resmi değere "çakılıyordu".
  Geri-test (Cuma→Cuma ΔN06 - Δproxy, 187 hafta, 2023-2026):
    A02-A17 (eski)  RMSE 2,98  |  2026: 3,28, maks 8,3 milyar USD
    A02-A14 (yeni)  RMSE 0,80  |  2026: 0,31, maks 0,7 milyar USD
  `python net_rezerv.py --gunluk-dogrula` bu tabloyu her koşuda yeniden üretir.

Cuma günlerinde günlük tahmin = haftalık resmi değer (ΔAnalitik = 0).

Doğrulama (24.04.2026):
  Brüt Rezerv         = 171.05 milyar USD   (Bloomberg: 171.1)
  Net Rezerv          =  54.23 milyar USD   (Bloomberg:  54.2)
  Swap Hariç Net Rez  =  36.39 milyar USD   (Bloomberg:  36.4)

Kullanım:
  python net_rezerv.py                 # haftalık snapshot + günlük seri
  python net_rezerv.py --validate      # 24.04.2026 ile karşılaştırma
  python net_rezerv.py --start 01-01-2025 --csv tarih_serisi.csv
  python net_rezerv.py --daily-only --start 01-04-2026  # sadece günlük seri
  python net_rezerv.py --swap-dogrula  # swap düzeltmesi ara değer hata ölçümü
  python net_rezerv.py --gunluk-dogrula # günlük proxy geri-testi (A02-A14 vs eski)
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import os
import re

import pandas as pd
import pdfplumber
import requests
import tcmb

# EVDS anahtari kaynak koda GOMULMEZ: once TTO_EVDS_KEY ortam degiskeni
# (CI'da depo secret'i), sonra bu klasordeki .evds_key dosyasi (.gitignore'da).
_ANAHTAR_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".evds_key")


def _evds_anahtari() -> str:
    anahtar = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if anahtar:
        return anahtar
    if os.path.exists(_ANAHTAR_DOSYA):
        try:
            with open(_ANAHTAR_DOSYA, encoding="utf-8") as f:
                anahtar = f.read().strip()
        except OSError as e:
            print(f"UYARI: {_ANAHTAR_DOSYA} okunamadi ({type(e).__name__}).")
            anahtar = ""
        if anahtar:
            return anahtar
    raise RuntimeError(
        "EVDS anahtari bulunamadi. export TTO_EVDS_KEY=<anahtar> ya da "
        f"{_ANAHTAR_DOSYA} dosyasina yazin (.gitignore'da)."
    )


API_KEY = _evds_anahtari()

SERIES = {
    # Stand-by Cari (haftalık - Cuma)
    "net_uluslararasi_rezerv_TL": "TP.AB.N06",
    "brut_doviz_rezerv_TL":       "TP.AB.N07",
    "brut_doviz_yukumluluk_TL":   "TP.AB.N08",
    "bankalar_doviz_mev_TL":      "TP.AB.N09",
    "imf_TL":                     "TP.AB.N10",
    "diger_yukumluluk_TL":        "TP.AB.N11",
    # Analitik bilanço (iş günü) — günlük delta için
    "dis_varliklar_TL":           "TP.AB.A02",   # A. Dış Varlıklar
    "bankalar_doviz_mev_gunluk_TL": "TP.AB.A14", # İç yük. > döviz mevduatı > Bankalar
    # A17 = Emisyon (Rezerv Para bileşeni). Eskiden yanlışlıkla "döviz
    # yükümlülüğü" diye buradaydı; günlük tahmin hatasının ana kaynağıydı.
    "emisyon_TL":                 "TP.AB.A17",
    # USD/TRY alış (günlük)
    "usdtry":                     "TP.DK.USD.A.YTL",
}

# IRFCL (Uluslararası Rezervler ve Döviz Likiditesi) — AYLIK, ay sonu.
# Haftalık PDF'teki II.2 / II.3 kalemlerinin resmi seri karşılığı; ay sonu
# tarihlerinde PDF ile milyon USD hassasiyetinde AYNI (bkz. irfcl_arsiv.py
# --dogrula). Swap hariç net rezervin tarihsel omurgası bu iki seri.
IRFCL_SERIES = {
    "ii2_M": "TP.DOVVARNC.K14",   # II.2 Yurt içi para karşılığı döviz forward/future (toplam)
    "ii3_M": "TP.DOVVARNC.K23",   # II.3 Diğer (repo/ticari/diğer borç-alacak, toplam)
}

WEEKLY_TABLES_PAGE = (
    "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/"
    "Odemeler+Dengesi+ve+Ilgili+Istatistikler/Uluslararasi+Rezervler+ve+Doviz+Likiditesi/"
    "Veri+(Tablolar)+-+Haftalik"
)

# Haftalık IRFCL gözlem arşivi (irfcl_arsiv.py doldurur, her koşuda canlı PDF
# noktası eklenir). Ay içi gerçek haftalık gözlemler burada birikiyor.
GOZLEM_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "irfcl_gozlem.csv")

# EVDS tek istekte yaklaşık 700 satırdan sonrasını sessizce kırpıyor (uzun
# aralık istendiğinde aralığın SONUNDAN geriye doğru dolduruyor). Bu yüzden
# istek yıllık parçalara bölünüyor — aksi halde --start geriye çekildiğinde
# tarihsel derinlik alınmıyor.
EVDS_PARCA_GUN = 366


# ----------------------------------------------------------------------------
# EVDS
# ----------------------------------------------------------------------------
def _read_evds_seri(client: "tcmb.Client", code: str, start: str,
                    end: str) -> pd.Series:
    """Tek seriyi yıllık parçalar hâlinde çekip birleştirir (satır sınırı için)."""
    t0 = pd.to_datetime(start, dayfirst=True)
    t1 = pd.to_datetime(end, dayfirst=True)
    parcalar: list[pd.Series] = []
    imlec = t0
    while imlec <= t1:
        son = min(imlec + pd.Timedelta(days=EVDS_PARCA_GUN - 1), t1)
        df = client.read(
            code,
            start=imlec.strftime("%d-%m-%Y"),
            end=son.strftime("%d-%m-%Y"),
        )
        if len(df):
            parcalar.append(df.iloc[:, 0])
        imlec = son + pd.Timedelta(days=1)
    if not parcalar:
        return pd.Series(dtype=float)
    s = pd.concat(parcalar)
    return s[~s.index.duplicated(keep="last")].sort_index()


def fetch_evds(start: str, end: str) -> pd.DataFrame:
    client = tcmb.Client(api_key=API_KEY)
    out: dict[str, pd.Series] = {}
    for label, code in SERIES.items():
        out[label] = _read_evds_seri(client, code, start, end)
    df = pd.concat(out, axis=1).sort_index()
    df["usdtry"] = df["usdtry"].ffill()
    return df


def fetch_irfcl_aylik(start: str, end: str) -> pd.DataFrame:
    """EVDS aylık IRFCL: II.2 ve II.3 (Milyon USD), ay SONU tarihine indekslenir.

    EVDS aylık serileri ayın 1'i etiketiyle döner; IRFCL'de değer ayın SON
    gününe aittir. Haftalık PDF ile hizalamak için indeks ay sonuna kaydırılır.
    """
    client = tcmb.Client(api_key=API_KEY)
    out: dict[str, pd.Series] = {}
    for label, code in IRFCL_SERIES.items():
        out[label] = _read_evds_seri(client, code, start, end)
    df = pd.concat(out, axis=1).sort_index().dropna(how="all")
    df.index = df.index + pd.offsets.MonthEnd(0)
    df["toplam_M"] = df["ii2_M"].fillna(0.0) + df["ii3_M"].fillna(0.0)
    df.index.name = "tarih"
    return df


def calculate_weekly_net_reserves(
    df: pd.DataFrame, swap_duzeltme_usd: pd.Series | None = None
) -> pd.DataFrame:
    """Haftalık (Cuma) net rezerv ve alt kalemler -- milyar USD."""
    weekly = df.dropna(subset=["net_uluslararasi_rezerv_TL"]).copy()
    for col, target in [
        ("net_uluslararasi_rezerv_TL", "net_rezerv_usd"),
        ("brut_doviz_rezerv_TL", "brut_rezerv_usd"),
        ("brut_doviz_yukumluluk_TL", "brut_yukumluluk_usd"),
        ("bankalar_doviz_mev_TL", "bankalar_doviz_mev_usd"),
        ("imf_TL", "imf_usd"),
        ("diger_yukumluluk_TL", "diger_yukumluluk_usd"),
    ]:
        weekly[target] = weekly[col] * 1_000.0 / weekly["usdtry"] / 1e9
    if swap_duzeltme_usd is not None:
        weekly["swap_duzeltme_usd"] = swap_duzeltme_usd.reindex(weekly.index)
        weekly["swap_haric_net_rezerv_usd"] = (
            weekly["net_rezerv_usd"] + weekly["swap_duzeltme_usd"]
        )
    return weekly


# ----------------------------------------------------------------------------
# Swap düzeltmesi (II.2 + II.3) — GERÇEK gözlemlerden
# ----------------------------------------------------------------------------
def swap_gozlemleri(start: str, end: str,
                    canli_pdf: dict | None = None) -> pd.DataFrame:
    """(II.2 + II.3) gerçek gözlem tablosu — milyar USD, tarih indeksli.

    Üç kaynak birleştirilir (çakışmada haftalık gözlem kazanır, çünkü tam o
    güne ait):
      1. EVDS aylık IRFCL (ay sonu)          → kaynak = "evds_aylik"
      2. irfcl_gozlem.csv (haftalık PDF arşivi) → kaynak = "irfcl_pdf"
      3. o anki canlı haftalık PDF              → kaynak = "irfcl_pdf"

    Uydurma/genişletme YOK: her satır yayımlanmış bir IRFCL gözlemidir.
    """
    aylik = fetch_irfcl_aylik(start, end)
    kayit = pd.DataFrame({
        "swap_duzeltme_usd": aylik["toplam_M"] / 1_000.0,
        "kaynak": "evds_aylik",
    })

    if os.path.exists(GOZLEM_CSV):
        ark = pd.read_csv(GOZLEM_CSV, index_col=0, parse_dates=True)
        haftalik = pd.DataFrame({
            "swap_duzeltme_usd": (ark["ii2_M"] + ark["ii3_M"]) / 1_000.0,
            "kaynak": "irfcl_pdf",
        })
        kayit = pd.concat([kayit, haftalik])

    if canli_pdf and "tarih" in canli_pdf:
        ii2 = (canli_pdf.get("II_2_acik_M", 0.0)
               + canli_pdf.get("II_2_fazla_M", 0.0))
        ii3 = canli_pdf.get("II_3_toplam_M", 0.0)
        kayit.loc[canli_pdf["tarih"]] = [(ii2 + ii3) / 1_000.0, "irfcl_pdf"]

    # Aynı tarihte hem aylık hem haftalık varsa haftalığı tut
    kayit = kayit.sort_values("kaynak")           # evds_aylik < irfcl_pdf
    kayit = kayit[~kayit.index.duplicated(keep="last")].sort_index()
    kayit.index.name = "tarih"
    return kayit


def swap_duzeltme_serisi(gozlem: pd.DataFrame, index: pd.DatetimeIndex,
                         ileri_tasima_gun: int = 21) -> pd.Series:
    """Gözlemleri istenen takvime taşır — zaman ağırlıklı doğrusal ara değer.

    Kurallar (kasıtlı olarak muhafazakâr):
      • İlk gözlemden ÖNCE  → NaN (geriye doğru uzatma YOK).
      • Gözlemler ARASINDA  → iki gerçek gözlem arasında zamana göre doğrusal
        ara değer. IRFCL swap pozisyonu vade defterinin doğal akışıyla değişir;
        iki yayım arasını doğrusal bağlamak, ay sonu değerini bir ay boyunca
        sabit tutmaktan (basamak) daha isabetli: elde 7 ay-içi gerçek haftalık
        gözlem varken ortalama |hata| ara değerde 0,41 / basamakta 0,91 milyar
        USD (%55 daha az). Ölçüm: `python net_rezerv.py --swap-dogrula`.
      • Son gözlemden SONRA → en fazla `ileri_tasima_gun` gün sabit taşınır
        (haftalık IRFCL ~1 hafta gecikmeli yayımlanır), sonrası NaN.

    Dönen seri milyar USD; NaN kalan yerlerde "swap hariç net rezerv" de
    hesaplanmaz — sahte doluluk üretilmez.
    """
    g = gozlem["swap_duzeltme_usd"].dropna().sort_index()
    g = g[~g.index.duplicated(keep="last")]   # union/interpolate tekrar kaldırmaz
    if g.empty:
        return pd.Series(index=index, dtype=float)

    birlesik = g.reindex(g.index.union(index)).sort_index()
    ara = birlesik.interpolate(method="time", limit_area="inside")
    ara = ara.reindex(index)

    # Son gözlemden sonrası: sınırlı ileri taşıma
    son_t, son_v = g.index[-1], g.iloc[-1]
    kuyruk = (index > son_t) & (index <= son_t + pd.Timedelta(days=ileri_tasima_gun))
    ara[kuyruk] = son_v
    ara[index > son_t + pd.Timedelta(days=ileri_tasima_gun)] = float("nan")
    ara[index < g.index[0]] = float("nan")
    return ara


def swap_gozlem_maskesi(gozlem: pd.DataFrame,
                        index: pd.DatetimeIndex) -> pd.Series:
    """İlgili tarih gerçek bir IRFCL gözlemi mi? (grafikte işaretlemek için)"""
    return pd.Series(index.isin(gozlem.index), index=index)


def calculate_daily_net_reserves(
    df: pd.DataFrame, swap_duzeltme_usd: pd.Series | None = None,
    swap_gozlem: pd.Series | None = None,
) -> pd.DataFrame:
    """Cuma anchor + analitik bilanço delta ile günlük net rezerv tahmini.

    Net Rezerv (T) = (N06_son_Cuma_TL + ΔAnalitik_TL(son_Cuma→T)) / USDTRY(T)
    ΔAnalitik = Δ(A02 Dış Varlıklar − A14 Bankaların Döviz Mevduatı)

    Cuma günlerinde delta = 0 ⇒ resmi haftalık değerle eşleşir.

    Parameters
    ----------
    df : EVDS dataframe (fetch_evds çıktısı)
    swap_duzeltme_usd : Optional. Tarihe göre (II.2 + II.3), milyar USD —
        `swap_duzeltme_serisi` çıktısı. Verilirse
        Swap Hariç Net Rezerv (T) = Net Rezerv (T) + swap_duzeltme(T).
        Düzeltmenin NaN olduğu tarihlerde swap hariç seri de NaN kalır.
    """
    out = df[["dis_varliklar_TL", "bankalar_doviz_mev_gunluk_TL",
              "usdtry"]].copy()
    # Dış Varlıklar - Bankaların Döviz Mevduatı (A02 - A14). N06'nın hafta
    # içinde gerçekten oynayan iki bacağı bunlar; IMF ve "diğer" yükümlülük
    # hafta içinde sabit kabul edilir (bkz. modül açıklaması + --gunluk-dogrula).
    out["analitik_net_TL"] = (
        out["dis_varliklar_TL"] - out["bankalar_doviz_mev_gunluk_TL"]
    )

    # Cuma anchor: TP.AB.N06 (TL) ve aynı Cumadaki analitik net (TL)
    # NOT: Cuma günü analitik bilanço yayımlanmamış olabilir (yayım gecikmesi).
    # Bu durumda anchor için en yakın ÖNCEKİ iş günü değeri kullanılır.
    n06 = df["net_uluslararasi_rezerv_TL"]
    out["anchor_n06_TL"] = n06.ffill()
    # Analitik veriyi önce ffill et (eksik günleri doldur), sonra anchor seç
    analitik_filled = out["analitik_net_TL"].ffill()
    out["anchor_analitik_TL"] = analitik_filled.where(n06.notna()).ffill()
    out["anchor_date"] = pd.Series(out.index, index=out.index).where(
        n06.notna()
    ).ffill()

    out["delta_analitik_TL"] = out["analitik_net_TL"] - out["anchor_analitik_TL"]
    out["net_rezerv_usd"] = (
        (out["anchor_n06_TL"] + out["delta_analitik_TL"])
        * 1_000.0 / out["usdtry"] / 1e9
    )

    # Brüt rezerv günlük (sadece dış varlıklardan):
    # Stand-by cari Brüt rezerv günlük olarak yok; analitik Dış Varlıklar
    # altın+döviz toplamı olduğu için yaklaşık brüt rezerv değeri verir.
    out["analitik_dis_varlik_usd"] = (
        out["dis_varliklar_TL"] * 1_000.0 / out["usdtry"] / 1e9
    )

    if swap_duzeltme_usd is not None:
        # Swap Hariç = Net Rezerv + (II.2 + II.3). Düzeltme artık TARİHE GÖRE
        # değişen gerçek IRFCL verisi; eskiden son PDF'in tek sabiti tüm geçmişe
        # yayılıyordu (2007'den bugüne aynı offset) — o davranış kaldırıldı.
        out["swap_duzeltme_usd"] = swap_duzeltme_usd.reindex(out.index)
        out["swap_haric_net_rezerv_usd"] = (
            out["net_rezerv_usd"] + out["swap_duzeltme_usd"]
        )
        # O tarihte IRFCL gözlemi var mı (yayımlanmış) yoksa ara değer mi?
        out["swap_gozlem"] = (
            False if swap_gozlem is None
            else swap_gozlem.reindex(out.index).fillna(False)
        )

    cols = [
        "usdtry", "analitik_dis_varlik_usd", "net_rezerv_usd",
        "delta_analitik_TL"
    ]
    if "swap_haric_net_rezerv_usd" in out.columns:
        cols += ["swap_duzeltme_usd", "swap_haric_net_rezerv_usd", "swap_gozlem"]
    return out[cols].dropna(subset=["net_rezerv_usd"])


# ----------------------------------------------------------------------------
# Haftalık IRFCL PDF parser
# ----------------------------------------------------------------------------
def _parse_number(s: str) -> float:
    s = s.strip().replace(".", "").replace(",", ".")
    return float(s) if s and s != "-" else 0.0


def _satir_toplami(ln: str) -> float | None:
    """II. bölüm satırından 'Toplam' sütununu çıkarır.

    Satır düzeni: <etiket> [dipnot no] Toplam  1-aya-kadar  2-3-ay  4ay-1yıl
    Dipnot numarası bazı sürümlerde var bazılarında yok (ör. 2021 PDF'lerinde
    '3. Diğer -5.486 ...' iken 2026'da '3. Diğer 3 3.736 ...'). Ayırt etmek için
    kimlik kullanılıyor: Toplam = üç vade kovasının toplamı. Son dört sayı bu
    kimliği sağlıyorsa ilki Toplam'dır; sağlamıyorsa satırdaki ilk sayı alınır.
    """
    sayilar = [_parse_number(x) for x in re.findall(r"-?[\d\.]+", ln)]
    if not sayilar:
        return None
    if len(sayilar) >= 4:
        d = sayilar[-4:]
        if abs(d[0] - (d[1] + d[2] + d[3])) < 1.0:
            return d[0]
    return sayilar[0]


def parse_weekly_pdf(pdf_bytes: bytes) -> dict:
    """RT*.pdf'inden referans tarih, brüt rezerv, II.2, II.3 (Milyon USD).

    NOT: Tarih PDF'in İÇİNDEN okunur, dosya adından değil. TCMB sunucusu
    RT<tarih>TR.pdf yoluna hangi tarih verilirse verilsin GÜNCEL PDF'i
    döndürüyor; dosya adına güvenmek yanlış tarihli kayda yol açar.
    """
    out: dict = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    lines = [ln.strip() for ln in text.split("\n")]

    # Referans tarih: I. bölüm başlığının hemen altındaki gg.aa.yyyy
    for ln in lines[:20]:
        m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", ln)
        if m:
            out["tarih"] = pd.Timestamp(int(m.group(3)), int(m.group(2)),
                                        int(m.group(1)))
            break

    for ln in lines:
        m = re.match(
            r"A\.\s*Resmi\s*rezerv\s*varl[ıi]klar[ıi]\s+\d?\s*([-\d\.,]+)\s*$", ln,
        )
        if m:
            out["resmi_rezerv_varliklari_M"] = _parse_number(m.group(1))
            break
    for ln in lines:
        if re.match(r"\(a\)\s*A[çc][ıi]k\s*pozisyonlar\s*\(-\)", ln):
            if "II_2_acik_M" not in out:
                deger = _satir_toplami(re.sub(r"^\(a\).*?\(-\)", "", ln))
                if deger is not None:
                    out["II_2_acik_M"] = deger
            continue
        if re.match(r"\(b\)\s*Fazla\s*pozisyonlar\s*\(\+\)", ln):
            if "II_2_fazla_M" not in out:
                deger = _satir_toplami(re.sub(r"^\(b\).*?\(\+\)", "", ln))
                if deger is not None:
                    out["II_2_fazla_M"] = deger
    for ln in lines:
        if re.match(r"3\.?\s*Di[ğg]er\b", ln):
            deger = _satir_toplami(re.sub(r"^3\.?\s*Di[ğg]er", "", ln))
            if deger is not None:
                out["II_3_toplam_M"] = deger
            break
    return out


def fetch_latest_weekly_pdf() -> bytes:
    """Sitedeki EN SON haftalık IRFCL PDF'ini indirir (tek hafta; arşiv yok).

    Referans tarih dosya adından DEĞİL PDF içinden okunur → parse_weekly_pdf.
    """
    page = requests.get(WEEKLY_TABLES_PAGE, timeout=30).text
    m = re.search(r"href=\"([^\"]*RT(\d{8})TR\.pdf[^\"]*)\"", page)
    if not m:
        raise RuntimeError("RT*.pdf linki bulunamadı")
    rel = m.group(1).replace("&amp;", "&")
    url = "https://www.tcmb.gov.tr" + rel
    return requests.get(url, timeout=60).content


def gozlem_arsivine_ekle(kalem: dict) -> None:
    """Canlı PDF gözlemini irfcl_gozlem.csv'ye ekler (gerçek haftalık birikim).

    TCMB geçmiş haftaları yayında tutmadığı için her koşu, o haftanın gerçek
    II.2/II.3 değerini kalıcılaştırır; zamanla ay içi gözlem yoğunluğu artar.
    """
    if not kalem or "tarih" not in kalem:
        return
    cols = ["ii2_M", "ii3_M", "kaynak"]
    if os.path.exists(GOZLEM_CSV):
        ark = pd.read_csv(GOZLEM_CSV, index_col=0, parse_dates=True)
    else:
        ark = pd.DataFrame(columns=cols,
                           index=pd.DatetimeIndex([], name="tarih"))
    ark.loc[kalem["tarih"], cols] = [
        kalem.get("II_2_acik_M", 0.0) + kalem.get("II_2_fazla_M", 0.0),
        kalem.get("II_3_toplam_M", 0.0),
        "irfcl_pdf",
    ]
    ark = ark[~ark.index.duplicated(keep="last")].sort_index()
    ark.index.name = "tarih"
    ark.to_csv(GOZLEM_CSV)


# ----------------------------------------------------------------------------
# Çıktılar
# ----------------------------------------------------------------------------
def latest_summary(weekly: pd.DataFrame, swap_pdf: dict | None,
                   pdf_date: str | None) -> str:
    last = weekly.iloc[-1]
    lines = [
        f"=== TCMB Net Uluslararası Rezerv  ({last.name:%d-%m-%Y}, Cuma) ===",
        f"  Brüt Döviz Rezervi    : {last['brut_rezerv_usd']:>8.2f} milyar USD",
        f"  Brüt Yükümlülükler    : {last['brut_yukumluluk_usd']:>8.2f} milyar USD",
        f"     - Bankalar Döviz   : {last['bankalar_doviz_mev_usd']:>8.2f} milyar USD",
        f"     - IMF              : {last['imf_usd']:>8.2f} milyar USD",
        f"     - Diğer            : {last['diger_yukumluluk_usd']:>8.2f} milyar USD",
        f"  Net Rezerv (TP.AB.N06): {last['net_rezerv_usd']:>8.2f} milyar USD",
        f"  USD/TRY (alış)        : {last['usdtry']:>8.4f}",
    ]
    if swap_pdf and "resmi_rezerv_varliklari_M" in swap_pdf:
        rrv = swap_pdf["resmi_rezerv_varliklari_M"] / 1000.0
        lines.insert(
            1,
            f"  I.A Resmi Rez. Varl.  : {rrv:>8.2f} milyar USD  (haftalık IRFCL)",
        )
    if swap_pdf:
        ii2 = (swap_pdf.get("II_2_acik_M", 0)
               + swap_pdf.get("II_2_fazla_M", 0)) / 1000.0
        ii3 = swap_pdf.get("II_3_toplam_M", 0) / 1000.0
        swap_haric = last["net_rezerv_usd"] + ii2 + ii3
        lines += [
            "",
            f"=== Haftalık IRFCL Tablosu  ({pdf_date}) ===",
            f"  II.2 Açık Pozisyon (-)  : {ii2:>8.2f} milyar USD",
            f"  II.3 Diğer (net)        : {ii3:>8.2f} milyar USD",
            f"  Net Swap Pozisyonu     : {ii2 + ii3:>8.2f} milyar USD",
            "",
            f"  Swap Hariç Net Rezerv  : {swap_haric:>8.2f} milyar USD",
        ]
    return "\n".join(lines)


def gunluk_dogrulama_raporu(raw: pd.DataFrame) -> str:
    """Günlük tahminin çekirdeği olan Δproxy'nin Cuma→Cuma geri-testi.

    Her resmi Cuma F için: hata = [N06(F) − N06(F−7)] − Δproxy(F−7→F), USD'ye
    F kuru ile çevrilir. Aday proxy'ler yan yana basılır ki seçim gerekçesi
    (A02−A14) her koşuda veriyle yeniden görülsün. Elle ayar yok: yalnız EVDS.
    """
    adaylar = {
        "A02-A14 (kullanılan)": raw["dis_varliklar_TL"]
                                - raw["bankalar_doviz_mev_gunluk_TL"],
        "A02      (yalnız dış varlık)": raw["dis_varliklar_TL"],
        "A02-A17 (eski; A17=emisyon)": raw["dis_varliklar_TL"] - raw["emisyon_TL"],
    }
    cuma = raw[raw["net_uluslararasi_rezerv_TL"].notna()]
    usd = raw["usdtry"].ffill().reindex(cuma.index)
    dN = cuma["net_uluslararasi_rezerv_TL"].diff()
    satirlar = ["=== Günlük tahmin geri-testi (Cuma→Cuma, milyar USD) ==="]
    for ad, p in adaylar.items():
        dP = p.ffill().reindex(cuma.index).diff()
        e = ((dN - dP) * 1000.0 / usd / 1e9).dropna()
        e26 = e[e.index.year == e.index.year.max()]
        satirlar.append(
            f"  {ad:<30} n={len(e):>3}  RMSE {float((e**2).mean())**0.5:5.2f}  "
            f"MAE {e.abs().mean():5.2f}  maks {e.abs().max():5.2f}   | "
            f"{e.index.year.max()}: RMSE {float((e26**2).mean())**0.5:5.2f}  "
            f"maks {e26.abs().max():5.2f}"
        )
    return "\n".join(satirlar)


def swap_dogrulama_raporu(gozlem: pd.DataFrame) -> str:
    """Ay içi haftalık gözlemlerle ara değer / basamak hatasını ölçer.

    Test kümesi: kaynak="irfcl_pdf" olan ve ay sonuna denk GELMEYEN gerçek
    haftalık gözlemler. Bu noktalar yalnızca EVDS aylık (ay sonu) gözlemlerden
    tahmin edilir; gerçek değerle farkı iki yöntem için raporlanır.
    """
    aylik = gozlem[gozlem["kaynak"] == "evds_aylik"]["swap_duzeltme_usd"]
    test = gozlem[gozlem["kaynak"] == "irfcl_pdf"]["swap_duzeltme_usd"]
    test = test[[t != t + pd.offsets.MonthEnd(0) for t in test.index]]
    test = test[(test.index >= aylik.index.min()) & (test.index <= aylik.index.max())]
    if test.empty:
        return "\n=== Swap düzeltmesi doğrulama ===\n  (ay içi gözlem yok)"

    birlesik = aylik.reindex(aylik.index.union(test.index)).sort_index()
    ara = birlesik.interpolate(method="time", limit_area="inside")
    basamak = birlesik.ffill()

    lines = ["", "=== Swap düzeltmesi doğrulama (ay içi gerçek IRFCL haftaları) ===",
             "Tarih      |  gerçek |  aradeğer(hata) | basamak(hata)"]
    h_ara, h_bas = [], []
    for t, v in test.items():
        e1, e2 = ara.loc[t] - v, basamak.loc[t] - v
        h_ara.append(abs(e1))
        h_bas.append(abs(e2))
        lines.append(f"{t:%Y-%m-%d} | {v:>7.2f} | {ara.loc[t]:>7.2f}"
                     f" ({e1:+5.2f}) | {basamak.loc[t]:>7.2f} ({e2:+5.2f})")
    n = len(h_ara)
    lines += [
        f"  n = {n} hafta | ortalama |hata|: "
        f"ara değer {sum(h_ara) / n:.2f} mlr USD, "
        f"basamak {sum(h_bas) / n:.2f} mlr USD",
    ]
    return "\n".join(lines)


def daily_summary(daily: pd.DataFrame, n: int = 30) -> str:
    """Son N iş günü için günlük seri."""
    show = daily.tail(n).copy()
    show["delta_analitik_milyar_TL"] = show["delta_analitik_TL"] / 1e6
    cols = ["usdtry", "analitik_dis_varlik_usd", "net_rezerv_usd"]
    headers = ["USD/TRY", "Brüt(USD)", "Net Rez(USD)"]
    if "swap_haric_net_rezerv_usd" in show.columns:
        cols.append("swap_haric_net_rezerv_usd")
        headers.append("Swap Hariç(USD)")

    lines = ["", f"=== Günlük Seri (son {len(show)} iş günü) ==="]
    lines.append("Tarih      | " + " | ".join(f"{h:>12}" for h in headers)
                 + " | Δ(brüt)→net")
    lines.append("-" * (15 + 14 * len(headers) + 16))

    prev_net = None
    for d, row in show.iterrows():
        cells = [f"{row[c]:>12.2f}" for c in cols]
        if prev_net is not None:
            chg = row["net_rezerv_usd"] - prev_net
            chg_s = f"{chg:+6.2f}"
        else:
            chg_s = "    -"
        lines.append(f"{d:%Y-%m-%d} | " + " | ".join(cells) + f" | {chg_s}")
        prev_net = row["net_rezerv_usd"]
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    # NOT: --start artık gerçekten uygulanıyor (eskiden yanlış kwarg adıyla
    # EVDS'e geçmediği için sessizce yok sayılıyordu). Varsayılan, haftalık
    # TP.AB.N06'nın EVDS'te başladığı tarih — tarihsel derinlik korunuyor.
    ap.add_argument("--start", default="01-01-2002")
    ap.add_argument("--end", default=dt.date.today().strftime("%d-%m-%Y"))
    # Günlük seri ayrı kırpılıyor: haftalık seri tüm tarihsel derinliği tutsun
    # ama günlük CSV (ve ondan çizilen grafik) makul bir pencerede kalsın.
    ap.add_argument("--daily-start", default="01-01-2023",
                    help="günlük seri başlangıcı (gg-aa-yyyy); haftalık seriyi "
                         "kırpmaz")
    # CSV yolları VARSAYILAN olarak proje klasöründeki dosyalar. Eskiden None'dı ve
    # yalnız açıkça verilirse yazılıyordu; cron/bat/guncelle.py hepsi parametresiz
    # çağırdığı için hat hesabı yapıp DOSYAYA YAZMIYORDU — grafik.py ve ozet_uret.py
    # eski CSV'yi okuyor, sayfa 3 hafta 03.08'de kaldı ve "✓" görünüyordu.
    # Yazmamak istenirse --no-csv.
    _burasi = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--csv", default=os.path.join(_burasi, "haftalik_rezerv.csv"),
                    help="haftalık seri CSV yolu (varsayılan: proje klasörü)")
    ap.add_argument("--daily-csv", default=os.path.join(_burasi, "gunluk.csv"),
                    help="günlük seri CSV yolu (varsayılan: proje klasörü)")
    ap.add_argument("--no-csv", action="store_true",
                    help="CSV yazma (yalnız ekrana bas)")
    ap.add_argument("--daily-window", type=int, default=20,
                    help="özette gösterilecek son iş günü sayısı")
    ap.add_argument("--validate", action="store_true",
                    help="24.04.2026 referans değerleriyle karşılaştır")
    ap.add_argument("--no-pdf", action="store_true",
                    help="Haftalık PDF'i indirme (sadece EVDS)")
    ap.add_argument("--daily-only", action="store_true",
                    help="haftalık özet basma, sadece günlük tablo")
    ap.add_argument("--swap-dogrula", action="store_true",
                    help="ay içi gerçek IRFCL gözlemleriyle ara değer/basamak "
                         "yönteminin hatasını ölç")
    ap.add_argument("--gunluk-dogrula", action="store_true",
                    help="günlük tahmin proxy'sinin (A02-A14) Cuma→Cuma "
                         "geri-testi; eski A02-A17 ile yan yana")
    args = ap.parse_args()

    raw = fetch_evds(args.start, args.end)

    swap_pdf, pdf_date = (None, None)
    if not args.no_pdf:
        swap_pdf = parse_weekly_pdf(fetch_latest_weekly_pdf())
        gozlem_arsivine_ekle(swap_pdf)
        if "tarih" in swap_pdf:
            pdf_date = f"{swap_pdf['tarih']:%d-%m-%Y}"

    # Swap düzeltmesi (II.2 + II.3): tarihe göre DEĞİŞEN gerçek IRFCL verisi.
    # Kaynaklar: EVDS aylık IRFCL (ay sonu) + haftalık PDF gözlem arşivi +
    # canlı PDF. Gözlem olmayan tarihlerde ara değer, ilk gözlemden önce ve
    # son gözlemden 3 haftadan fazla sonra NaN.
    gozlem = swap_gozlemleri(args.start, args.end, swap_pdf)
    swap_duz = swap_duzeltme_serisi(gozlem, raw.index)
    swap_gzm = swap_gozlem_maskesi(gozlem, raw.index)

    weekly = calculate_weekly_net_reserves(raw, swap_duz)
    daily = calculate_daily_net_reserves(raw, swap_duz, swap_gzm)
    if args.daily_start:
        daily = daily.loc[pd.to_datetime(args.daily_start, dayfirst=True):]

    if not args.daily_only:
        print(latest_summary(weekly, swap_pdf, pdf_date))
    print(daily_summary(daily, n=args.daily_window))

    if args.swap_dogrula:
        print(swap_dogrulama_raporu(gozlem))
    if args.gunluk_dogrula:
        print(gunluk_dogrulama_raporu(raw))

    if args.validate:
        ref = {"brut": 171.1, "net": 54.2, "swap_haric": 36.4}
        if "2026-04-24" in weekly.index.strftime("%Y-%m-%d").to_list():
            row = weekly.loc["2026-04-24"]
            print("\n=== Doğrulama (24.04.2026) ===")
            print(f"  Brüt    -> hesap: {row['brut_rezerv_usd']:.2f} | "
                  f"resmi: {ref['brut']}")
            print(f"  Net     -> hesap: {row['net_rezerv_usd']:.2f} | "
                  f"resmi: {ref['net']}")
            # Swap hariç artık 24.04.2026'ya AİT swap düzeltmesiyle hesaplanıyor
            # (eskiden son PDF'in sabiti kullanılıyordu — tarih uyumsuzdu).
            if "swap_haric_net_rezerv_usd" in weekly.columns:
                sh = row["swap_haric_net_rezerv_usd"]
                print(f"  S.Har. -> hesap: {sh:.2f} | resmi: {ref['swap_haric']}"
                      f"  (swap düzeltmesi: {row['swap_duzeltme_usd']:+.2f})")

    if not args.no_csv:
        weekly.to_csv(args.csv)
        daily.to_csv(args.daily_csv)
        print(f"\nCSV kaydedildi: {args.csv}")
        print(f"Günlük CSV kaydedildi: {args.daily_csv}  (son: {daily.index[-1]:%d.%m.%Y})")


if __name__ == "__main__":
    main()
