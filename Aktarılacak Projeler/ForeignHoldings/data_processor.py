"""
Veri işleme modülü
Kümülatif hesaplamalar ve YTD veri hazırlama
"""

import pandas as pd


def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ham veriyi işler ve temizler

    Args:
        df: Ham EVDS verisi (Tarih, Hisse, DIBS sütunları)

    Returns:
        İşlenmiş DataFrame
    """
    df = df.copy()

    # Tarih sütununu datetime'a çevir (eğer değilse)
    if not pd.api.types.is_datetime64_any_dtype(df['Tarih']):
        df['Tarih'] = pd.to_datetime(df['Tarih'], errors='coerce')

    # Tarihe göre sırala
    df = df.sort_values('Tarih').reset_index(drop=True)

    # Kalan tekil boşlukları 0 kabul et. Serinin HENÜZ BAŞLAMADIĞI haftalar
    # fetcher'da atıldı; buraya gelen bir NaN, yayımlanmış bir hafta içinde
    # tek serinin boş kalması demektir (fetcher ekrana uyarı basar).
    df['Hisse'] = df['Hisse'].fillna(0)
    df['DIBS'] = df['DIBS'].fillna(0)

    # Toplam hesapla
    df['Toplam'] = df['Hisse'] + df['DIBS']

    # Yıl ve hafta bilgilerini ekle (YTD için)
    df['Year'] = df['Tarih'].dt.year

    # HAFTA = gözlemin takvim yılı içindeki kaçıncı Cuma olduğu (1..53).
    # ISO hafta numarası DEĞİL. Neden: seri HAFTALIK(CUMA); 1 Ocak bir Cuma'ya
    # denk geldiğinde (2010, 2016, 2021) o gözlemin ISO hafta numarası bir
    # ÖNCEKİ yıla ait 53 olur. ISO ile çizilince yılın İLK gözlemi grafiğin en
    # sağına, 53. haftaya düşüyor ve 2021 YTD çizgisi yıl sonundan başa doğru
    # geri sıçrıyordu.
    #
    # Hesap: yılın ilk Cuma'sı bulunur, gözlem ondan kaç hafta sonrasıysa +1.
    # Gözlem sırasına göre saymak (cumcount) YANLIŞ olurdu: seri 11-09-2020'de
    # başladığı için 2020'nin ilk gözlemi 1. haftaya düşer ve diğer yılların
    # Ocak ayıyla üst üste binerdi — oysa o gözlem yılın 37. haftasıdır.
    yil_basi = pd.to_datetime(dict(year=df['Year'], month=1, day=1))
    # Yılın, gözlemle aynı haftagününe denk gelen ilk günü (seri Cuma ise ilk Cuma)
    ilk_ayni_gun = yil_basi + pd.to_timedelta(
        (df['Tarih'].dt.weekday - yil_basi.dt.weekday) % 7, unit='D'
    )
    df['Week'] = ((df['Tarih'] - ilk_ayni_gun).dt.days // 7) + 1

    return df


def calculate_cumulative(df: pd.DataFrame) -> pd.DataFrame:
    """
    Kümülatif toplamları hesaplar (serinin başlangıcından itibaren)

    Args:
        df: İşlenmiş veri

    Returns:
        Kümülatif değerler eklenmiş DataFrame
    """
    df = df.copy()

    # Düz kümülatif toplam. (Eskiden "ilk sıfır olmayan gözlemden başla" mantığı
    # vardı; o mantık, EVDS'in seri başlamadan önce döndürdüğü boş satırların
    # sıfırla doldurulmasını telafi etmek içindi. Boş satırlar artık fetcher'da
    # atıldığı için ilk satır zaten ilk GERÇEK gözlem — düz cumsum aynı sonucu
    # verir ve "sıfır değerli gerçek bir hafta" ile "veri yok" karışmaz.)
    df['Hisse_Cumulative'] = df['Hisse'].cumsum()
    df['DIBS_Cumulative'] = df['DIBS'].cumsum()
    df['Toplam_Cumulative'] = df['Hisse_Cumulative'] + df['DIBS_Cumulative']

    return df


def prepare_ytd_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    YTD (Year-to-Date) verilerini hazırlar
    Her yıl için hafta hafta kümülatif toplamları hesaplar

    Args:
        df: İşlenmiş veri

    Returns:
        YTD verileri içeren DataFrame
    """
    df = df.copy()

    ytd_list = []

    for year in sorted(df['Year'].unique()):
        year_data = df[df['Year'] == year].copy()
        year_data = year_data.sort_values('Tarih').reset_index(drop=True)

        # Yıl içinde hafta hafta kümülatif toplam
        year_data['Hisse_YTD'] = year_data['Hisse'].cumsum()
        year_data['DIBS_YTD'] = year_data['DIBS'].cumsum()
        year_data['Toplam_YTD'] = year_data['Hisse_YTD'] + year_data['DIBS_YTD']

        if len(year_data) > 0:
            ytd_list.append(year_data)

    if len(ytd_list) == 0:
        return pd.DataFrame()

    # Tüm yılları birleştir
    df_ytd = pd.concat(ytd_list, ignore_index=True)

    return df_ytd
