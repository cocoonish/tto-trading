# EVDS Yurtdışı Yerleşikler DIBS ve Hisse Senedi Takip Sistemi

Bu proje, TCMB EVDS (Elektronik Veri Dağıtım Sistemi) üzerinden yurtdışı yerleşiklerin DIBS ve hisse senedi kesin alım-satım verilerini çekerek görselleştiren bir sistemdir.

## Özellikler

- **Kümülatif Grafikler**: İlk değişim noktasından başlayarak DIBS, Hisse ve Toplam kümülatif toplamları
- **YTD Karşılaştırmalı Grafikler**: Her yıl için hafta hafta karşılaştırmalı grafikler
- **İnteraktif Grafikler**: Plotly ile hover özellikli, M USD cinsinden gösterim
- **Dual Axis**: DIBS ve Hisse bir eksende, Toplam ikincil eksende

## Kurulum

1. Gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

2. EVDS API anahtarınızı alın:
   - https://evds2.tcmb.gov.tr adresine gidin
   - Kayıt olun ve API anahtarınızı alın

3. API anahtarını ayarlayın:
   - `.env` dosyası oluşturun: `cp .env.example .env`
   - `.env` dosyasına `EVDS_API_KEY=your_api_key_here` ekleyin
   - Veya `main.py` dosyasındaki `EVDS_API_KEY` değişkenini güncelleyin

## Kullanım

```bash
python main.py
```

Grafikler `charts/` klasörüne HTML formatında kaydedilir. Tarayıcıda açarak interaktif olarak inceleyebilirsiniz.

## Parametreler

Tüm parametreler `main.py` dosyasının en üstünde tanımlanmıştır:

- `EVDS_API_KEY`: EVDS API anahtarı
- `EVDS_HISSE_CODE`: Hisse senedi seri kodu (varsayılan: TP.MKNETHAR.M7)
- `EVDS_DIBS_CODE`: DIBS seri kodu (varsayılan: TP.MKNETHAR.M8)
- `START_DATE`: Başlangıç tarihi (format: DD-MM-YYYY)
- `END_DATE`: Bitiş tarihi (None ise bugün)
- `OUTPUT_DIR`: Grafik çıktı klasörü
- `CHART_WIDTH`, `CHART_HEIGHT`: Grafik boyutları
- `CHART_THEME`: Plotly tema
- `CURRENCY_UNIT`: Para birimi etiketi

## Çıktılar

- `cumulative_chart.html`: Kümülatif toplamlar grafiği
- `ytd_hisse.html`: YTD Hisse karşılaştırması
- `ytd_dibs.html`: YTD DIBS karşılaştırması
- `ytd_toplam.html`: YTD Toplam karşılaştırması

## Notlar

- EVDS API'den veri çekme işlemi internet bağlantısı gerektirir
- İlk çalıştırmada veri çekme işlemi biraz zaman alabilir
- Grafikler interaktif olduğu için HTML formatında kaydedilir

