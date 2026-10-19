---
title: 'FX Gün İçi Stratejiler 3: Kırılım Kuralları — Ne Yapıyorlar, Ne Verdiler, Stop ve Hedef Neyi Değiştirirdi'
description: "Sekiz kırılım kuralı tek tek: açılış aralığı, Asya aralığı, New York ilk saati, iç mum, sıkışma, önceki günün tepe ve dibi, pivot kırılımı. Her kural için sade tanım, backtest sonucu ve bütün stop/hedef bileşimlerinin 2024 sonrası sonucu."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders', 'kirilim']
durum: 'arsiv'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Sekiz kırılım kuralının her biri sade tanımı, backtest sonucu ve stop × hedef tablosuyla. Hiçbir stop/hedef bileşimi bu kuralların birini 2024 sonrasında artıya taşımıyor; en yakın gelen Asya aralığı kırılımı sıfıra yaklaşıyor ama geçmiyor."
seviye: 'giris'
onkosul:
  - fx-gunici-sonuc
---

<div class="not gezinme"><span class="etiket">Arşiv</span> Bu ders gün içi FX kurallarının ayrıntılı sınamasındandır ve arşivdedir. Gün içi seri şimdi açılış, fiksing ve haber anlarının oyun planı olarak beş derste: [1 · İlk mumu okumak](/arastirma/fx-oyun-okuma/) · [2 · Açılışlar](/arastirma/fx-oyun-acilislar/) · [3 · Fiksingler](/arastirma/fx-oyun-fiksingler/) · [4 · Haber mumları](/arastirma/fx-oyun-haberler/) · [5 · Backtest](/arastirma/fx-oyun-backtest/).</div>

Kırılım kuralları aynı fikirden çıkar: fiyat belli bir aralıkta bir süre durduktan sonra o aralığın dışına çıkarsa, o
yönde devam eder. Aralık bazen bir seansın ilk dakikalarıdır, bazen önceki günün tepesi ve dibi, bazen dar bir sıkışma.
Bu derste sekiz kural var. Her biri için üç şey yazılı:

1. **Kural** — ne zaman, hangi yönde girilir; varsayılan stop ve hedef.
2. **Sonuç** — varsayılan ayarla, dört parite birlikte, maliyetten sonra.
3. **Stop ve hedef tablosu** — kuralın öbür bütün ayarları aynı kalıp yalnız stop ve hedef değiştirilseydi 2024 →
   döneminde ne olurdu. Altındaki cümle "çalışır hale getirebilir miydik" sorusunun cevabı.

Tablolardaki "R" işlemin riskidir (girişle stop arası). İşlem başına {{= "−0,10" }} R, riske edilen tutarın onda birini kaybetmek
demektir. Bütün mumlar varsayılanda 15 dakikalıktır.

## Özet

{{! kisa_kart_ozet fx-gunici-kirilim }}

{{! sekil kisa-aralik-kirilim "Stop ve hedef nerede olursa olsun — kırılım kuralları" }}

Gri çizgi bir kuralın bütün stop/hedef bileşimlerinin 2024 → sonucunu kapsıyor; çizginin sağ ucu sıfırın solundaysa,
o kural için hiçbir stop/hedef seçimi artı sonuç vermedi demektir.

## Londra açılış aralığı kırılımı (ORB)

- **Kural.** Londra açılışından sonraki ilk 15 dakikanın ({{! tsi "" "Londra 08:00–08:15" }}) en yükseği ve en düşüğü
  aralıktır. Aralığın dışında kapanan ilk mumun yönünde girilir; günde tek işlem, son giriş
  {{! tsi "" "Londra 12:00" }}.
- **Varsayılan stop ve hedef.** Stop aralığın karşı ucunda; hedef yok, pozisyon gün sonunda kapanır.

{{! kisa_kart orb }}

## Asya aralığı kırılımı

- **Kural.** Asya seansının aralığı ({{! tsi "" "Londra 00:00–08:00" }}) çıkarılır. Londra açılışından sonra aralığın
  dışında kapanan ilk mumun yönünde girilir; günde tek işlem, son giriş {{! tsi "" "Londra 11:00" }}.
- **Varsayılan stop ve hedef.** Stop aralığın ortasında; hedef 1R (stop kadar uzakta).

{{! kisa_kart asya }}

## New York sabah aralığı kırılımı

- **Kural.** New York'ta sabahın ilk saatinin aralığı ({{! tsi "" "New York 08:00–09:00" }}) çıkarılır; ardından aralığın
  dışında kapanan ilk mumun yönünde girilir. Günde tek işlem, son giriş {{! tsi "" "New York 12:00" }}.
- **Varsayılan stop ve hedef.** Stop aralığın karşı ucunda; hedef yok, gün sonunda çıkılır.

{{! kisa_kart nyib_0800 }}

## New York hisse açılışı aralığı kırılımı

- **Kural.** Aynı kural, New York hisse piyasasının açılışından başlayan ilk saatle
  ({{! tsi "" "New York 09:30–10:30" }}). Son giriş {{! tsi "" "New York 12:00" }}.
- **Varsayılan stop ve hedef.** Stop aralığın karşı ucunda; hedef yok, gün sonunda çıkılır.

{{! kisa_kart nyib_0930 }}

## İç mum kırılımı

- **Kural.** İç mum, bir önceki mumun (ana mum) tamamen içinde kalan mumdur. Sonraki üç mumdan biri ana mumun dışında
  kapanırsa o yönde girilir; olmazsa kurulum iptal. Yalnız Londra açılışından New York öğlesine kadar
  ({{! tsi "→" "Londra 08:00" "New York 12:00" }}).
- **Varsayılan stop ve hedef.** Stop ana mumun karşı ucunda; hedef 2R.

{{! kisa_kart icmum }}

## Sıkışma kırılımı (Bollinger bantları Keltner kanalının içinde)

- **Kural.** Bollinger bantlarının ikisi de Keltner kanalının içine girdiğinde piyasa "sıkışmış" sayılır. En az altı mum
  süren sıkışma bitince, beş mum içinde sıkışma kutusunun (o mumların en yükseği ile en düşüğü) dışında kapanan ilk
  mumun yönünde girilir. Son sinyal {{! tsi "" "New York 16:00" }}.
- **Varsayılan stop ve hedef.** Stop kutunun karşı ucunda; hedef 2R.

{{! kisa_kart sikisma }}

## Önceki günün tepe ve dibinin kırılımı

- **Kural.** Bir önceki FX gününün en yükseği ve en düşüğü seviyedir (FX günü {{! tsi "" "New York 17:00" }} başlar).
  Londra açılışından sonra bu seviyelerden birini kesen ilk kapanışın yönünde girilir; günde tek işlem, son giriş
  {{! tsi "" "New York 14:00" }}.
- **Varsayılan stop ve hedef.** Stop sinyal mumunun karşı ucunda; hedef 2R.

{{! kisa_kart pdhl }}

## Pivot kırılımı

- **Kural.** Önceki günün yüksek, düşük ve kapanışından pivot (P) ile R1 ve S1 seviyeleri hesaplanır. Bir kapanış R1'i
  yukarı ya da S1'i aşağı keserse kesiş yönünde girilir; seviye başına günde tek işlem, pencere
  {{! tsi "→" "Londra 08:00" "New York 14:00" }}.
- **Varsayılan stop ve hedef.** Stop sinyal mumunun karşı ucunda; hedef 2R.

{{! kisa_kart pivot_kirilim }}

## Bu dersten çıkan

- Sekiz kırılım kuralının hiçbiri varsayılan ayarıyla 2024 → döneminde kazandırmadı.
- Stop ve hedefi değiştirmek kazanma oranını belirgin biçimde oynatıyor; işlem başına sonucu sıfırın üstüne
  çıkarmıyor. Sıfıra en yakın bileşimler çoğunlukla geniş stoplu ve uzak hedefli (ya da hedefsiz) olanlar: stop
  uzadıkça aynı maliyet riskin daha küçük bir parçası oluyor.
- 2018–2023'e bakarak seçilen stop/hedef de 2024 →'de eksi kaldı.

Sonraki ders: dönüş kuralları.
