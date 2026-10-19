---
title: 'FX Gün İçi Stratejiler 4: Dönüş Kuralları — Sahte Kırılım, VWAP, Pivot ve Fiksing Sonrası'
description: "Altı dönüş kuralı tek tek: açılış aralığının, Asya aralığının ve önceki günün tepe/dibinin sahte kırılımı, VWAP'a dönüş, pivottan dönüş ve fiksing sonrası dönüş. Her kural için sade tanım, backtest sonucu ve bütün stop/hedef bileşimlerinin 2024 sonrası sonucu."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders', 'donus']
durum: 'arsiv'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Altı dönüş kuralının her biri sade tanımı, backtest sonucu ve stop × hedef tablosuyla. Hiçbir stop/hedef bileşimi bunlardan birini 2024 sonrasında artıya taşımıyor."
seviye: 'giris'
onkosul:
  - fx-gunici-sonuc
---

<div class="not gezinme"><span class="etiket">Arşiv</span> Bu ders gün içi FX kurallarının ayrıntılı sınamasındandır ve arşivdedir. Gün içi seri şimdi açılış, fiksing ve haber anlarının oyun planı olarak beş derste: [1 · İlk mumu okumak](/arastirma/fx-oyun-okuma/) · [2 · Açılışlar](/arastirma/fx-oyun-acilislar/) · [3 · Fiksingler](/arastirma/fx-oyun-fiksingler/) · [4 · Haber mumları](/arastirma/fx-oyun-haberler/) · [5 · Backtest](/arastirma/fx-oyun-backtest/).</div>

Dönüş kuralları kırılımın tersine oynar: fiyat bir seviyenin dışına çıkıp geri dönerse, ya da ortalamasından çok
uzaklaşırsa, geri döneceğine bahis girilir. Bu derste altı kural var ve her birinde aynı üç parça duruyor: kural, sonuç ve
stop × hedef tablosu. Tabloların okunuşu bir önceki dersteki gibidir; mumlar varsayılanda 15 dakikalıktır.

## Özet

{{! kisa_kart_ozet fx-gunici-donus }}

{{! sekil kisa-aralik-donus "Stop ve hedef nerede olursa olsun — dönüş kuralları" }}

## Açılış aralığının sahte kırılımı

- **Kural.** Londra açılış aralığı (ilk 15 dakika, {{! tsi "" "Londra 08:00–08:15" }}) çıkarılır. Bir mum aralığın
  dışında kapanır, sonraki iki mumdan biri yeniden içeride kapanırsa kırılımın tersi yönünde girilir. Seviye başına günde
  tek işlem, son giriş {{! tsi "" "Londra 14:00" }}.
- **Varsayılan stop ve hedef.** Stop sahte kırılımın ucunda (kırılım mumundan dönüş mumuna kadarki en uç fiyat);
  hedef 1R.

{{! kisa_kart sahte_orb }}

## Asya aralığının sahte kırılımı

- **Kural.** Aynı kural, Asya aralığıyla ({{! tsi "" "Londra 00:00–08:00" }}). Son giriş {{! tsi "" "Londra 14:00" }}.
- **Varsayılan stop ve hedef.** Stop sahte kırılımın ucunda; hedef 1R.

{{! kisa_kart sahte_asya }}

## Önceki günün tepe ve dibinin sahte kırılımı

- **Kural.** Aynı kural, önceki FX gününün en yükseği ve en düşüğüyle. Pencere Londra açılışından New York öğleden
  sonrasına ({{! tsi "→" "Londra 08:00" "New York 14:00" }}).
- **Varsayılan stop ve hedef.** Stop sahte kırılımın ucunda; hedef 1R.

{{! kisa_kart sahte_pdhl }}

## VWAP'a dönüş

- **Kural.** VWAP, Londra açılışından beri hacim ağırlıklı ortalama fiyattır (hacim, veri sağlayıcının işlem hacmi). Fiyat VWAP'tan iki standart
  sapmadan fazla uzaklaşıp yeniden bu bandın içinde kapanırsa VWAP yönünde girilir. Açılıştan sonraki ilk saat sinyal
  alınmaz; son sinyal {{! tsi "" "New York 16:00" }}.
- **Varsayılan stop ve hedef.** Stop bant dışındaki gezintinin ucunda; hedef VWAP'ın kendisi.

{{! kisa_kart vwap_donus }}

## Pivottan dönüş

- **Kural.** Önceki günün yüksek, düşük ve kapanışından pivot (P), R1 ve S1 hesaplanır. Fiyat R1'e değip altında
  kapanırsa satış, S1'e değip üstünde kapanırsa alış. Seviye başına günde tek işlem, pencere
  {{! tsi "→" "Londra 08:00" "New York 14:00" }}.
- **Varsayılan stop ve hedef.** Stop sinyal mumunun seviyenin ötesindeki ucunda; hedef pivot (P).

{{! kisa_kart pivot_donus }}

## Fiksing sonrası dönüş

- **Kural.** Londra fiksinginden ({{! tsi "" "Londra 16:00" }}) önceki son 15 dakikalık mumun tersi yönünde, fiksingde
  girilir ve iki mum (30 dakika) sonra çıkılır. Fikir, fiksinge giden emir akışının bittiği anda fiyatın geri döneceğidir.
- **Varsayılan stop ve hedef.** Stop yok, hedef yok: çıkış süreyle. Bu kuralda R, girişteki oynaklık (1 ATR) birimidir.

{{! kisa_kart fiks_donus }}

## Bu dersten çıkan

- Altı dönüş kuralının hiçbiri varsayılan ayarıyla 2024 → döneminde kazandırmadı.
- Kapanış stopu ve yakın hedef bu kuralların çoğunda kazanma oranını yükseltiyor; ama kazançlar küçüldüğü için sonuç
  yine eksi. Stop ve hedef seçimi bu kuralların hiçbirini artıya taşımıyor.
- 2018–2023'e bakarak seçilen stop/hedef de 2024 →'de eksi kaldı.

Sonraki ders: akış ve haber kuralları.
