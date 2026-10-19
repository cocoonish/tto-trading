---
title: 'FX Gün İçi Stratejiler 5: Akış ve Haber Kuralları — Fiksing, Gün İçi Momentum, VWAP Geri Çekilmesi ve Beş Haber Kuralı'
description: "Sekiz kural tek tek: Londra fiksingi momentumu, Londra açılışından New York öğleden sonrasına momentum, VWAP geri çekilmesi ve haber anında kullanılan beş kural (kırılım, fade, straddle, başarısız kırılım, geri çekilme sonrası devam). Her kural için sade tanım, backtest sonucu ve bütün stop/hedef bileşimlerinin 2024 sonrası sonucu."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders', 'haber']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt · resmî yayım takvimleri'
ozet: "Akış ve haber kurallarının her biri sade tanımı, backtest sonucu ve stop × hedef tablosuyla. Haber anındaki başarısız kırılım kuralında süreyle çıkış iki dönemde de artı, ama işlem sayısı çok az ve sonuç dört paritenin yarısında eksi; öbür kuralları stop ya da hedef güvenilir biçimde artıya taşımıyor."
seviye: 'giris'
onkosul:
  - fx-gunici-sonuc
---

Bu dersteki kurallar bir seviyeye değil bir **ana** bakar: büyük emirlerin toplandığı Londra fiksingi, iki büyük seansın
devri ve önemli bir veri açıklaması. Önce üç akış kuralı, sonra haber anında kullanılan beş kural. Tabloların okunuşu ilk
iki kural dersindeki gibidir.

Haber kurallarının sınandığı olaylar: ABD tarım dışı istihdam ve enflasyon verisi, Fed kararı ve başkanın basın
toplantısı (dört paritede), Avrupa Merkez Bankası kararı ve basın toplantısı (EUR/USD) ve İngiltere Merkez Bankası kararı
(GBP/USD). Haber kurallarında mumlar 5 dakikalıktır; "ilk haber mumu" açıklamanın olduğu dakikadan başlayan mumdur.

## Özet

{{! kisa_kart_ozet fx-gunici-akis-haber }}

{{! sekil kisa-aralik-akis-haber "Stop ve hedef nerede olursa olsun — akış ve haber kuralları" }}

## Fiksing momentumu

- **Kural.** Londra fiksinginden önceki 5 dakikalık mumun ({{! tsi "" "Londra 15:50–15:55" }}) yönünde, fiksingden
  beş dakika önce girilir ve tam fiksingde ({{! tsi "" "Londra 16:00" }}) çıkılır. Fikir, fiksinge giden büyük emirlerin
  son dakikalarda fiyatı aynı yöne itmeye devam etmesidir.
- **Varsayılan stop ve hedef.** Stop yok, hedef yok: çıkış saatle. R, girişteki oynaklık (1 ATR) birimidir.

{{! kisa_kart fiks_momentum }}

Bu kuralın her gün uygulanan hâli kaybettiriyor; yalnız **ay sonu** günlerindeki işlemleri GBP/USD'de iki dönemde de
artıda kaldı{{? O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.net > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.oos.ay_sonu.net > 0 }} (birinci ders). Ay sonu ayrımı sonuçlar görüldükten sonra yapıldığı için orada ileriye dönük izlenecek bir
aday olarak duruyor.

## Londra açılışından New York öğleden sonrasına momentum

- **Kural.** Londra açılışından sonraki ilk saatin ({{! tsi "" "Londra 08:00–09:00" }}) yönü kaydedilir; aynı yönde
  {{! tsi "" "New York 12:00" }} girilir, {{! tsi "" "New York 16:00" }} çıkılır.
- **Varsayılan stop ve hedef.** Stop yok, hedef yok: çıkış saatle. R, girişteki oynaklık (1 ATR) birimidir.

{{! kisa_kart momentum }}

## VWAP geri çekilmesi

- **Kural.** Son 12 mumun hepsi VWAP'ın aynı yanında kapandıysa trend var sayılır. Fiyat VWAP'a değip trend yönünde
  kapanırsa trend yönünde girilir. VWAP Londra açılışından hesaplanır, ilk saat sinyal alınmaz, son sinyal
  {{! tsi "" "New York 16:00" }}.
- **Varsayılan stop ve hedef.** Stop sinyal mumunun karşı ucunda; hedef 2R.

{{! kisa_kart vwap_cekilme }}

## Haber kırılımı (N1)

- **Kural.** İlk haber mumu kapanınca onun yönünde, bir sonraki mumun açılışında girilir.
- **Varsayılan stop ve hedef.** Stop ilk haber mumunun karşı ucunda; hedef 1R.

{{! kisa_kart n1 }}

## Haber fade'i (N2)

- **Kural.** İlk haber mumu olağan oynaklığın (ATR) iki katından fazla hareket ettiyse, sonraki üç mumdan biri ters yönde
  kapandığında hareketin tersine girilir.
- **Varsayılan stop ve hedef.** Stop o ana kadarki hareketin ucunda; hedef haberden önceki fiyat.

{{! kisa_kart n2 }}

## Haber öncesi aralığın kırılımı — straddle (N3)

- **Kural.** Haberden önceki altı mumun (yarım saat) en yükseği ve en düşüğü aralıktır. Haberden sonra aralığın dışında
  kapanan ilk mumun yönünde girilir (en geç altıncı mumda).
- **Varsayılan stop ve hedef.** Stop aralığın karşı ucunda; hedef 1R.

{{! kisa_kart n3 }}

## Başarısız haber kırılımı (N4)

- **Kural.** İlk haber mumu haber öncesi aralığın (altı mum) dışında kapanır, ikinci mum yeniden aralığın içinde kapanırsa
  ilk hareketin tersine girilir.
- **Varsayılan stop ve hedef.** Stop ilk iki mumun ucunda; hedef aralığın öbür ucu.

{{! kisa_kart n4 }}

Bu tabloda süreyle çıkış (on iki mum, yani bir saat sonra) iki dönemde de artı{{? O.kisa.kart.n4.iki_arti > 0 }}. Seride stop ve hedefi 2018–2023'e bakarak
seçip 2024 →'de de artı kalan bir bileşim olarak dikkat çekiyor. Ama kural sayılması için üç engel var: işlem çok az
(haber günleri ve aralık dışı kapanış şartı birlikte seyrek), artı dört paritenin yarısında toplanıyor, öbür yarısında sonuç eksi, ve bu kadar
işlemle görülen sonuç şanstan ayrılamıyor. Ay sonu fiksingi gibi, ancak ileriye dönük izlenebilecek bir aday.

## Geri çekilme sonrası devam (N5)

- **Kural.** İlk haber mumu en az yarım ATR hareket ettiyse, sonraki altı mum içinde fiyatın bu hareketin yarısını geri
  vermesi beklenir; ardından ilk hareket yönünde kapanan ilk mumda girilir.
- **Varsayılan stop ve hedef.** Stop geri çekilmenin ucunda; hedef ilk haber mumunun ucu.

{{! kisa_kart n5 }}

## Bu dersten çıkan

- Akış ve haber kurallarının hiçbiri varsayılan ayarıyla 2024 → döneminde güvenilir biçimde kazandırmadı.
- Stop ve hedef değişikliği bu kurallarda da kazanma oranını oynatıyor, sonucu artıya taşımıyor. İki istisna var:
  başarısız haber kırılımında süreyle çıkış (iki dönemde de artı, ama az işleme ve dört paritenin yarısına dayanıyor) ve
  haber fade'inde bir bileşim (2024 →'de sıfırın hemen üstünde, 2018–2023'te eksi; seçilebilecek bir ayar değildi){{? O.kisa.kart.n2.oos_arti > 0 and O.kisa.kart.n2.iki_arti == 0 }}.
- İki ileriye dönük aday var: GBP/USD ay sonu fiksingi ve başarısız haber kırılımında süreyle çıkış. İkisi de
  sonuçlar görüldükten sonra öne çıktı; kanıt ancak bugünden sonraki işlemlerle gelir.

Sonraki ders: stop ve hedefin genel aritmetiği — kazanma oranı neden kâr değildir.
