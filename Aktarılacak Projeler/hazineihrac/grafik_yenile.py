#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grafik yenileme — scraper ÇALIŞTIRMADAN, mevcut CSV'lerden yeniden üretim.

main.py'deki grafik fonksiyonlarını (create_borrowing_performance_chart,
create_maturity_charts) diskteki CSV'lerle besler. Veri çekme (scrape) yapılmaz;
main.py yalnızca import edilir (modül seviyesinde ağ erişimi yoktur).

Kullanım (proje kökünde; main.py'nin import'ları gerektiğinden ana python3 ile —
.conda ortamında aiohttp yok):
  python3 grafik_yenile.py

Çıktılar:
  - hedef_gerceklesme.html  (hazine_hedef_gerceklesme.csv'den)
  - hazine_vade_analizi.csv (hazine_ihale_verileri.csv'den YENİDEN KURULUR)
  - vade_analizi.html       (o tablodan)

Vade tablosu neden burada yeniden kuruluyor: tablo ihale verisinin saf bir
türevidir ve eskiden yalnız tam kip (main.py) yazıyordu. Hafif kipin üç adımı
(vade_proj, ozet_uret, tablo_uret) onu OKUYOR; üretenin adım listesinde
görünmediği bir dosya, ihale verisi değiştiği gün sessizce eskir. Aynı adım
ihale tablosunu tek vade tanımına çeker (main.vade_normalize — gün/365) ve
yalnız bir değer değiştiyse dosyaya yazar; sonraki adımlar hep aynı cetveli
okur.

Not: web çıktılarının kalanı (ihrac_hacmi, faiz_gelisimi, talep_analizi …)
web_cikti_tahmin.py ile üretilir — o da yalnız CSV/JSON okur.
Siteye kopyalama sonrası ev stili uygulanır:
  python3 "../../site/tools/plotly_stil.py" <dosyalar>
"""

from pathlib import Path

import pandas as pd

from main import (
    TreasuryAuctionScraper,
    COMPARISON_CSV,
    CSV_OUTPUT,
    WADE_CSV,
    HEDEF_GERCEKLESME_HTML,
    HTML_OUTPUT,
    vade_normalize,
)

KOK = Path(__file__).resolve().parent


def main() -> None:
    # 1) Hedef vs gerçekleşme
    kaynak = KOK / COMPARISON_CSV
    comparison_df = pd.read_csv(kaynak, encoding="utf-8-sig")
    TreasuryAuctionScraper.create_borrowing_performance_chart(
        None, comparison_df, str(KOK / HEDEF_GERCEKLESME_HTML)
    )
    print(f"{HEDEF_GERCEKLESME_HTML:24s} <- {kaynak.name} ({len(comparison_df)} ay)")

    # 2) İhale tablosu tek vade tanımında mı? Değilse yalnız vade sütunu değişir.
    kaynak = KOK / CSV_OUTPUT
    ham = kaynak.read_text(encoding="utf-8-sig")
    ihale = pd.read_csv(kaynak, encoding="utf-8-sig")
    ihale_n = vade_normalize(ihale)
    if ihale_n.to_csv(index=False) != ham.replace("\r\n", "\n"):
        ihale_n.to_csv(kaynak, index=False, encoding="utf-8-sig")
        print(f"{CSV_OUTPUT:24s} vade tek tanıma çekildi (gün/365)")

    # 3) Vade analizi — ihale tablosundan
    wam_df = TreasuryAuctionScraper.calculate_weighted_average_maturity(None, ihale_n)
    if wam_df.empty:
        raise SystemExit("vade tablosu kurulamadı — ihale verisinde ölçülebilir vade yok")
    wam_df.to_csv(KOK / WADE_CSV, index=False, encoding="utf-8-sig")
    TreasuryAuctionScraper.create_maturity_charts(
        None, wam_df, str(KOK / HTML_OUTPUT)
    )
    print(f"{WADE_CSV:24s} <- {kaynak.name} ({len(wam_df)} ay)")
    print(f"{HTML_OUTPUT:24s} <- {WADE_CSV}")


if __name__ == "__main__":
    main()
