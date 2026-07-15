"""TCMB Net Uluslararası Rezerv Hesaplama Scripti.

Hesaplama yöntemi (Bloomberg / Mahfi Eğilmez / Paraanaliz uyumu):

  Net Rezerv (USD)  = TP.AB.N06 (Stand-By Cari "2A Net Uluslararası Rezervler",
                      Bin TL) / TP.DK.USD.A.YTL  (Cuma kapanışı)

  Swap Hariç Net Rezerv (Cuma) = Net Rezerv + II.2 + II.3
                      ‣ II.2 = "Yurt İçi Para Karşılığında Döviz Forward ve
                        Future toplam açık+fazla pozisyon" (negatif)
                      ‣ II.3 = "Diğer" (repo/ticari/diğer borç-alacak net)
                      II.2 ve II.3 haftalık IRFCL PDF'inden parse edilir.

Günlük tahmin (Cuma anchor + analitik bilanço delta):

  Net Rezerv (T)      = (TP.AB.N06_son_Cuma + ΔAnalitik_TL(son_Cuma→T))
                        / TP.DK.USD.A.YTL(T)
                        ΔAnalitik = Δ(TP.AB.A02 - TP.AB.A17)

  Swap Hariç Net Rezerv (T) = Net Rezerv (T) + (II.2 + II.3) son Cuma
                        (yabancı banka swap'ı kısa vadede sabit varsayılır)

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
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import re

import pandas as pd
import pdfplumber
import requests
import tcmb

API_KEY = "5ILfFTTp8n"

SERIES = {
    # Stand-by Cari (haftalık - Cuma)
    "net_uluslararasi_rezerv_TL": "TP.AB.N06",
    "brut_doviz_rezerv_TL":       "TP.AB.N07",
    "brut_doviz_yukumluluk_TL":   "TP.AB.N08",
    "bankalar_doviz_mev_TL":      "TP.AB.N09",
    "imf_TL":                     "TP.AB.N10",
    "diger_yukumluluk_TL":        "TP.AB.N11",
    # Analitik bilanço (iş günü) — günlük delta için
    "dis_varliklar_TL":           "TP.AB.A02",
    "doviz_yukumluluk_TL":        "TP.AB.A17",
    # USD/TRY alış (günlük)
    "usdtry":                     "TP.DK.USD.A.YTL",
}

WEEKLY_TABLES_PAGE = (
    "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/"
    "Odemeler+Dengesi+ve+Ilgili+Istatistikler/Uluslararasi+Rezervler+ve+Doviz+Likiditesi/"
    "Veri+(Tablolar)+-+Haftalik"
)


# ----------------------------------------------------------------------------
# EVDS
# ----------------------------------------------------------------------------
def fetch_evds(start: str, end: str) -> pd.DataFrame:
    client = tcmb.Client(api_key=API_KEY)
    out: dict[str, pd.Series] = {}
    for label, code in SERIES.items():
        df = client.read(code, start_date=start, end_date=end)
        out[label] = df.iloc[:, 0]
    df = pd.concat(out, axis=1).sort_index()
    df["usdtry"] = df["usdtry"].ffill()
    return df


def calculate_weekly_net_reserves(df: pd.DataFrame) -> pd.DataFrame:
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
    return weekly


def calculate_daily_net_reserves(
    df: pd.DataFrame, swap_haric_anchor_usd: dict[pd.Timestamp, float] | None = None
) -> pd.DataFrame:
    """Cuma anchor + analitik bilanço delta ile günlük net rezerv tahmini.

    Net Rezerv (T) = (N06_son_Cuma_TL + ΔAnalitik_TL(son_Cuma→T)) / USDTRY(T)

    Cuma günlerinde delta = 0 ⇒ resmi haftalık değerle eşleşir.

    Parameters
    ----------
    df : EVDS dataframe (fetch_evds çıktısı)
    swap_haric_anchor_usd : Optional. {Cuma tarihi: o Cuma için Swap Hariç Net
        Rezerv USD} — varsa günlük "Swap Hariç" sütunu eklenir (yabancı banka
        swap'ı kısa vadede sabit varsayılır, yani delta'sı = ΔNet Rezerv).
    """
    out = df[["dis_varliklar_TL", "doviz_yukumluluk_TL", "usdtry"]].copy()
    out["analitik_net_TL"] = (
        out["dis_varliklar_TL"] - out["doviz_yukumluluk_TL"]
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

    if swap_haric_anchor_usd:
        anchor_series = pd.Series(swap_haric_anchor_usd).sort_index()
        anchor_series.index = pd.to_datetime(anchor_series.index)
        # Anchor'ları aynı Cumalara hizala
        anchor_aligned = anchor_series.reindex(out.index)
        out["anchor_swap_haric_usd"] = anchor_aligned.ffill()
        out["delta_usd"] = out["net_rezerv_usd"] - (
            out["anchor_n06_TL"] * 1_000.0 / out["usdtry"] / 1e9
        ).where(n06.notna()).ffill()
        out["swap_haric_net_rezerv_usd"] = (
            out["anchor_swap_haric_usd"] + out["delta_usd"]
        )

    cols = [
        "usdtry", "analitik_dis_varlik_usd", "net_rezerv_usd",
        "delta_analitik_TL"
    ]
    if "swap_haric_net_rezerv_usd" in out.columns:
        cols.append("swap_haric_net_rezerv_usd")
    return out[cols].dropna(subset=["net_rezerv_usd"])


# ----------------------------------------------------------------------------
# Haftalık IRFCL PDF parser
# ----------------------------------------------------------------------------
def _parse_number(s: str) -> float:
    s = s.strip().replace(".", "").replace(",", ".")
    return float(s) if s and s != "-" else 0.0


def parse_weekly_pdf(pdf_bytes: bytes) -> dict[str, float]:
    """RT*.pdf'inden brüt rezerv, II.2, II.3 değerleri (Milyon USD)."""
    out: dict[str, float] = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    lines = [ln.strip() for ln in text.split("\n")]

    for ln in lines:
        m = re.match(
            r"A\.\s*Resmi\s*rezerv\s*varl[ıi]klar[ıi]\s+\d?\s*([-\d\.,]+)\s*$", ln,
        )
        if m:
            out["resmi_rezerv_varliklari_M"] = _parse_number(m.group(1))
            break
    for ln in lines:
        m = re.match(r"\(a\)\s*A[çc][ıi]k\s*pozisyonlar\s*\(-\)\s+([-\d\.,]+)", ln)
        if m and "II_2_acik_M" not in out:
            out["II_2_acik_M"] = _parse_number(m.group(1))
            continue
        m = re.match(r"\(b\)\s*Fazla\s*pozisyonlar\s*\(\+\)\s+([-\d\.,]+)", ln)
        if m and "II_2_fazla_M" not in out:
            out["II_2_fazla_M"] = _parse_number(m.group(1))
    for ln in lines:
        m = re.match(r"3\.?\s*Di[ğg]er\s+\d+\s+([-\d\.,]+)", ln)
        if m:
            out["II_3_toplam_M"] = _parse_number(m.group(1))
            break
    return out


def fetch_latest_weekly_pdf() -> tuple[bytes, str]:
    page = requests.get(WEEKLY_TABLES_PAGE, timeout=30).text
    m = re.search(r"href=\"([^\"]*RT(\d{8})TR\.pdf[^\"]*)\"", page)
    if not m:
        raise RuntimeError("RT*.pdf linki bulunamadı")
    rel = m.group(1).replace("&amp;", "&")
    url = "https://www.tcmb.gov.tr" + rel
    pdf = requests.get(url, timeout=60).content
    return pdf, m.group(2)


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
    ap.add_argument("--start", default="01-01-2025")
    ap.add_argument("--end", default=dt.date.today().strftime("%d-%m-%Y"))
    ap.add_argument("--csv", default=None,
                    help="haftalık seri CSV yolu")
    ap.add_argument("--daily-csv", default=None,
                    help="günlük seri CSV yolu")
    ap.add_argument("--daily-window", type=int, default=20,
                    help="özette gösterilecek son iş günü sayısı")
    ap.add_argument("--validate", action="store_true",
                    help="24.04.2026 referans değerleriyle karşılaştır")
    ap.add_argument("--no-pdf", action="store_true",
                    help="Haftalık PDF'i indirme (sadece EVDS)")
    ap.add_argument("--daily-only", action="store_true",
                    help="haftalık özet basma, sadece günlük tablo")
    args = ap.parse_args()

    raw = fetch_evds(args.start, args.end)
    weekly = calculate_weekly_net_reserves(raw)

    swap_pdf, pdf_date = (None, None)
    if not args.no_pdf:
        pdf_bytes, ymd = fetch_latest_weekly_pdf()
        swap_pdf = parse_weekly_pdf(pdf_bytes)
        pdf_date = f"{ymd[6:8]}-{ymd[4:6]}-{ymd[:4]}"

    # Haftalık swap hariç anchor (her Cuma için tek değer): bu sürümde sadece
    # son IRFCL'den hesaplanan Cuma noktası anchor olarak konuyor; geçmiş
    # Cumalar için aynı II.2+II.3 sabit alınır (yaklaşık -- swap kompozisyonu
    # haftadan haftaya küçük dalgalanır).
    sh_anchor_usd: dict | None = None
    if swap_pdf:
        ii2 = (swap_pdf.get("II_2_acik_M", 0)
               + swap_pdf.get("II_2_fazla_M", 0)) / 1000.0
        ii3 = swap_pdf.get("II_3_toplam_M", 0) / 1000.0
        sh_anchor_usd = {
            d: row["net_rezerv_usd"] + ii2 + ii3
            for d, row in weekly.iterrows()
        }

    daily = calculate_daily_net_reserves(raw, sh_anchor_usd)

    if not args.daily_only:
        print(latest_summary(weekly, swap_pdf, pdf_date))
    print(daily_summary(daily, n=args.daily_window))

    if args.validate:
        ref = {"brut": 171.1, "net": 54.2, "swap_haric": 36.4}
        if "2026-04-24" in weekly.index.strftime("%Y-%m-%d").to_list():
            row = weekly.loc["2026-04-24"]
            print("\n=== Doğrulama (24.04.2026) ===")
            print(f"  Brüt    -> hesap: {row['brut_rezerv_usd']:.2f} | "
                  f"resmi: {ref['brut']}")
            print(f"  Net     -> hesap: {row['net_rezerv_usd']:.2f} | "
                  f"resmi: {ref['net']}")
            if swap_pdf:
                ii2 = (swap_pdf.get("II_2_acik_M", 0)
                       + swap_pdf.get("II_2_fazla_M", 0)) / 1000.0
                ii3 = swap_pdf.get("II_3_toplam_M", 0) / 1000.0
                sh = row["net_rezerv_usd"] + ii2 + ii3
                print(f"  S.Har. -> hesap: {sh:.2f} | resmi: {ref['swap_haric']}")

    if args.csv:
        weekly.to_csv(args.csv)
        print(f"\nCSV kaydedildi: {args.csv}")
    if args.daily_csv:
        daily.to_csv(args.daily_csv)
        print(f"Günlük CSV kaydedildi: {args.daily_csv}")


if __name__ == "__main__":
    main()
