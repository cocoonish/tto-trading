---
title: 'FX Gün İçi Stratejiler 6: Akış — Fiksing Momentumu, Gün İçi Momentum, VWAP Geri Çekilmesi'
description: "Fiyata değil akışa bakan üç kural, dört majör paritede ve 2018–2026 bid/ask verisiyle: WM/R 16:00 fiksingine giden dakikalarda itişin yönünde işlem (ay sonu ayrı), Londra'nın ilk saatinin New York öğleden sonrasını öngörüp öngörmediği (Newey–West regresyonuyla) ve gün içi trendde VWAP'a geri çekilmede trend yönünde giriş. Kural, örnek günler, sonuç, maliyet, rastgele yön sınaması, koşullar ve hüküm."
pubDate: 2026-10-16
tags: ['fx', 'gun-ici', 'fiksing', 'momentum', 'vwap', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Öngörülebilir saatlerde gelen akışın izini süren üç kural: fiksinge giden emirler, günün ilk hareketini öğleden sonra tamamlayan katılımcılar ve trendin ortalama fiyatına dönen alıcılar. Her birinin fade dersindeki karşılığıyla yan yana, maliyetten sonra ne bıraktığı."
seviye: 'orta'
onkosul:
  - fx-gunici-giris
  - fx-gunici-fade
---

Kırılım ve fade kuralları bir **seviyeye** bakar: bir aralığın ucu, dünün tepesi, bir pivot. Bu dersin üç kuralı
seviyeye değil **akışa** bakar — belli saatlerde gelen, büyüklüğü ve yönü önceden bilinmese de varlığı bilinen emir
akışına. Bu seride sınanan iki an var: Londra 16:00'daki WM/R fiksingi (fon yöneticilerinin, endeks fonlarının,
kurumsal hazinelerin değerleme ve işlem kuru) ve günün ilk büyük akışını taşıyan Londra açılışı. Döviz piyasasında
başka akış anları da var ve burada sınanmadı: Tokyo fiksingi (Tokyo 09:55, TSİ 03:55; Japon şirketlerinin günlük
kur ihtiyacının toplandığı an, USD/JPY'de) ve New York 10:00 opsiyon vade kesimi (TSİ 17:00, ABD kış saatinde
18:00). Üçüncü
kural akışı saatte değil fiyatta arar: gün içi bir trendde VWAP, o gün işlem yapanların ortalama maliyetidir ve geri
çekilme kuralı oraya dönen fiyatın trendi taşıyanlarla karşılaşacağına bahis yapar.

İkisinin fade dersinde bir karşılığı var ve bu ders onları yan yana okur: fiksing momentumu fiksing dönüşünün, VWAP
geri çekilmesi VWAP dönüşünün tersidir. Gün içi momentumun karşılığı yoktur; yerine kuralın ölçtüğü
ilişkinin kendisi, stop ve hedef taşımayan bir regresyonla ayrıca sınanır.

İki kural stop'suzdur (fiksing momentumu ve gün içi momentum): işlem planlanan saatte kapanır ve R birimi stop
uzaklığı değil girişteki ATR'dir. Sonuç tablolarının okunuşu öbür derslerle aynıdır; yalnız işlemlerin anatomisi
tablosunda o satır "R birimi" adını taşır ve bir risk değil oynaklık ölçüsüdür: stop olmadığı için kayıp 1R'de
durmaz.

## WM/R 16:00 fiksingi — momentum

{{! strateji fiks_momentum }}

## Gün içi momentum

{{! strateji momentum }}

## VWAP geri çekilmesi

{{! strateji vwap_cekilme }}

## Üç kuralın özeti

{{! ders_ozet }}

Fade dersindeki karşılıklarıyla yan yana — aynı saatin ve aynı ortalamanın iki tarafı:

{{! ders_ozet fiks_momentum fiks_donus vwap_cekilme vwap_donus }}

Bir kuralın kaybetmesi tersinin kazanacağı anlamına gelmez. İki taraf aynı makası öder; fiyat hareketi iki tarafa
da yetmediğinde ikisi birden kaybeder. Bu tablonun okunuşu bu yüzden "hangisi daha az kaybediyor" değil, "maliyetten
önce bir yön var mı" sorusudur ve cevabı her bölümün sonuç tablosunun brüt satırında.

<div class="pratik">
  <span class="etiket">Pratik — akış</span>

{{! pratik_islem vwap_cekilme "Alıştırma 1" kaybeden }}

{{! pratik_atr momentum "Alıştırma 2" tuzak }}

</div>

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
