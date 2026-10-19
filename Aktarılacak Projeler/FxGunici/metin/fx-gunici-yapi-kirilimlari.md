---
title: 'FX Gün İçi Stratejiler 3: Yapı Kırılımları — İç Mum, Sıkışma, Önceki Gün Tepe/Dip, Pivot'
description: "Bir fiyat yapısının ya da referans seviyesinin kırılmasına dayanan dört kural, dört majör paritede ve 2018–2026 bid/ask verisiyle: iç mum (inside bar) kırılımı, Bollinger–Keltner sıkışması, önceki günün tepe ve dibinin kırılımı ve klasik (salon) pivotlarının (R1/S1) kırılımı. Kural, örnek günler, örneklem içi ve dışı sonuç, maliyet, rastgele yön sınaması, koşullar, kontrol listesi ve hüküm."
pubDate: 2026-10-17
tags: ['fx', 'gun-ici', 'kirilim', 'inside-bar', 'pivot', 'backtest', 'ders']
durum: 'arsiv'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Seansın saatine değil fiyatın kendi yapısına bakan dört kırılım kuralı: dar bir mumun, sakin bir oynaklık döneminin, dünün uçlarının ve pivot seviyelerinin kırılması. Dördünde de örneklem dışında (2024 →) yön seçimi hiçbir paritede rastgele yönden ayrışmıyor{{! rastgele_tum_istisna icmum sikisma pdhl pivot_kirilim }} ve maliyetten sonra kanıtlanmış bir kenar yok.{{! kural_iddia rastgele_yok icmum sikisma pdhl pivot_kirilim }}{{! kural_iddia calisan_yok icmum sikisma pdhl pivot_kirilim }}"
seviye: 'orta'
onkosul:
  - fx-gunici-giris
  - fx-gunici-seans-kirilimlari
---

<div class="not gezinme"><span class="etiket">Arşiv</span> Bu ders gün içi FX kurallarının ayrıntılı sınamasındandır ve arşivdedir. Gün içi seri şimdi açılış, fiksing ve haber anlarının oyun planı olarak beş derste: [1 · İlk mumu okumak](/arastirma/fx-oyun-okuma/) · [2 · Açılışlar](/arastirma/fx-oyun-acilislar/) · [3 · Fiksingler](/arastirma/fx-oyun-fiksingler/) · [4 · Haber mumları](/arastirma/fx-oyun-haberler/) · [5 · Backtest](/arastirma/fx-oyun-backtest/).</div>

Seans kırılımları saati seçer: Londra açılışı, New York'un sabahı. Bu dersin dört kuralı saati değil **yapıyı**
seçer. İç mum, bir mumun bir öncekinin içinde kalmasıyla oluşan küçük bir sıkışmadır. Bollinger–Keltner sıkışması aynı
fikrin istatistiksel biçimidir: kapanışların dağılımı mumların büyüklüğüne göre olağandışı daralmıştır. Önceki günün
tepe ve dibi ile klasik (salon) pivotları ise herkesin aynı anda baktığı seviyelerdir; güçlerini bir iktisadi içerikten değil
izlenmelerinden alırlar.

Yapı kuralları gün içinde birden çok kez sinyal üretebilir; aynı anda tek pozisyon taşındığı için bir sinyal, açık
bir pozisyon varken gelirse atlanır. İç mum ve sıkışmada bunun ne kadar sık olduğu kendi bölümlerinde ölçülüyor. Dört kuralın ikisinin
fade karşılığı var: önceki gün tepe/dip ve pivotun dönüş biçimleri fade dersinde aynı seviyelerle ölçülüyor; iç mumun
ve sıkışmanın karşılığı yok.

## İç mum (inside bar) kırılımı

{{! strateji icmum }}

## Bollinger–Keltner sıkışması

{{! strateji sikisma }}

## Önceki gün tepe/dip kırılımı (PDH/PDL)

{{! strateji pdhl }}

## Pivot kırılımı

{{! strateji pivot_kirilim }}

## Dört kuralın özeti

{{! ders_ozet }}

<div class="pratik">
  <span class="etiket">Pratik — yapı kırılımları</span>

{{! pratik_islem icmum "Alıştırma 1" kaybeden }}

{{! pratik_islem pdhl "Alıştırma 2" }}

</div>

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
