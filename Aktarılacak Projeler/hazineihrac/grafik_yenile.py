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
  - vade_analizi.html       (hazine_vade_analizi.csv'den)

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
    WADE_CSV,
    HEDEF_GERCEKLESME_HTML,
    HTML_OUTPUT,
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

    # 2) Vade analizi
    kaynak = KOK / WADE_CSV
    wam_df = pd.read_csv(kaynak, encoding="utf-8-sig")
    TreasuryAuctionScraper.create_maturity_charts(
        None, wam_df, str(KOK / HTML_OUTPUT)
    )
    print(f"{HTML_OUTPUT:24s} <- {kaynak.name} ({len(wam_df)} ay)")


if __name__ == "__main__":
    main()
