# TCMB EN 24/17 Replikasyonu — "Son Dönem Yiyecek Hizmetleri Sektörü Fiyatlama Gelişmeleri"

Atabek Demirhan & Bahça (TCMB Ekonomi Notları 2024-17) çalışmasının kamuya açık
veriyle replikasyonu ve **Temmuz 2026'ya** güncellenmesi.

## Çalıştırma

```bash
python3 src/run_all.py
```

Gereksinimler: `pandas, requests, matplotlib, openpyxl, xlrd, pdfplumber, playwright`
(MEDAS hasadı için `python3 -m playwright install chromium`; `data/raw/medas_*.xls`
dosyaları mevcutsa Playwright'a gerek kalmaz).

## Veri kaynakları

| Kaynak | İçerik | Dönem |
|---|---|---|
| TCMB EVDS3 API | TÜFE (2025=100, COICOP-2018, **2005'e geri taşınmış**, 5'li düzey); TÜFE (2003=100, arşiv); Yİ-ÜFE; Yeni Kiracı Kira Endeksi | 2005/01–2026/07 |
| TÜİK MEDAS | **Tüketici Madde Fiyatları (2003=100)** — 40 madde (8 yemek hizmeti + 32 gıda girdisi) | 2005/01–**2022/04** (yayın durdu) |
| TÜİK MEDAS | Tarım-ÜFE (2020=100) tür detayı: sığır-besi (01.42), kümes (01.47), koyun-keçi (01.45) | 2020/01–2026/06 |
| TÜİK Veri Portalı | Hizmet ciro endeksi (2015=100, arşiv); TÜFE ağırlık tabloları | — |
| Resmî Gazete / AÜTK | Brüt asgari ücret (2024'te ara zam yok; 2025: 26.005,50; 2026: 33.030) | 2013–2026 |

## Yöntem özeti ve proxy etiketleri

- Maliyet ağırlıkları: **%21 işgücü, %49 gıda, %5 enerji, %10 kira, %15 diğer** (notun Tablo 4'ü).
- 13 tarif, notun ekindeki paylarla birebir; tarif bileşenleri TÜİK maddelerine eşlendi (`src/endeks.py`).
- **PROXY 1:** TÜİK madde *endeksi* kamuya açık değil → madde *ortalama fiyatı* rölatifi kullanıldı.
- **PROXY 2:** Nisan 2022'de madde fiyatı yayını durdu → sonrası COICOP-2018 5'li grup endeksleriyle splice;
  dana/tavuk ayrımı Tarım-ÜFE tür kaması ile korundu (kapatılabilir: `tur_duzeltme=False`).
- **PROXY 3:** Fiyat tarafında kırmızı et/tavuk ayrımı TÜİK yapısında yok (kebap/döner maddeleri ortak) →
  fark yalnızca maliyet tarafından gelir (notun kendisi TCMB mikro fiyat tabanını kullanmıştı).
- 2026 baz değişimi: geri taşınmış 2025=100 serisi eski serinin birebir ölçeklemesi (aylık fark ≤0,007 puan) → zincirleme sorunsuz.

## Çıktılar (`output/`)

- `grafikler/grafik_01…14.png` — orijinal formatta, Temmuz 2026'ya uzatılmış (G13-14'te üçüncü sütun: Temmuz 2026).
- `seriler.xlsx` — ham + endeksli tüm seriler, meta ve proxy etiketleri, 16 sekme.
- `karsilastirma_tablosu.csv` — hedef vs replikasyon vs güncel + sapma gerekçeleri.
- `duyarlilik.csv` — 3 ağırlık seti × 3 kira senaryosu × tür-kaması açık/kapalı (18 koşu).
- `katki_ayristirma.csv` — Tem-2024→Tem-2026 maliyet artışı kalem katkıları.
- `degerlendirme_notu.md` — 1 sayfalık sonuç ve değerlendirme.
- `log/` — kaynak-tarih damgalı indirme logları, MEDAS hasat ekran kayıtları.

## Ana bulgular (Temmuz 2026)

Fiyat/maliyet oranları (2013 Ocak=1): ev yemekleri **1,27** (Tem-24: 1,27), kırmızı et **1,26** (1,20),
tavuk **1,51** (1,41), fast-food **1,68** (1,58; uzun dönem ort. 1,17 = notla birebir). 2023'te açılan makas
**kapanmadı; yüksek platoya oturdu**, fast-food'da açılma sürüyor. Kâr marjı düzeyi iki yoldan raporlanır:
çıpalı senaryo (TURYİD bandı) ve çıpasız food-cost oranları (`src/marj_seviye.py`). Ayrıntı: `output/degerlendirme_notu.md`.
