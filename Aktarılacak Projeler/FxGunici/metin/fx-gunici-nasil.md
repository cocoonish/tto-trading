---
title: 'FX Gün İçi Stratejiler 2: Adım Adım — Hangi Saatte Ne Olursa Ne Yapılır'
description: "22 gün içi FX kuralının uygulanışı, grafik üstünde: hangi saatte hangi seviye işaretlenir, hangi mum kapanınca hangi yönde girilir, stop nereye konur, ne zaman çıkılır. Her kural için gerçek bir günün grafiği, adımlar numaralı, saatler TSİ."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'strateji', 'ders', 'uygulama']
durum: 'arsiv'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "22 kuralın her biri için adım adım uygulama: hangi saatte ne işaretlenir, hangi mum kapanınca hangi yönde girilir, stop nereye konur, ne zaman çıkılır. Her kural gerçek bir günün grafiğinde numaralı adımlarla gösteriliyor; saatler TSİ."
seviye: 'giris'
onkosul:
  - fx-gunici-sonuc
---

<div class="not gezinme"><span class="etiket">Arşiv</span> Bu ders gün içi FX kurallarının ayrıntılı sınamasındandır ve arşivdedir. Gün içi seri şimdi açılış, fiksing ve haber anlarının oyun planı olarak beş derste: [1 · İlk mumu okumak](/arastirma/fx-oyun-okuma/) · [2 · Açılışlar](/arastirma/fx-oyun-acilislar/) · [3 · Fiksingler](/arastirma/fx-oyun-fiksingler/) · [4 · Haber mumları](/arastirma/fx-oyun-haberler/) · [5 · Backtest](/arastirma/fx-oyun-backtest/).</div>

Bu ders kuralların **nasıl uygulandığını** gösterir; sonuçları sonraki üç derstedir. Her kural için:

- **Adımlar** — hangi saatte neye bakılır, hangi mum kapanınca hangi yönde girilir, stop nereye konur, ne zaman çıkılır.
- **Grafik** — gerçek bir gün (EUR/USD), adımlar grafikte aynı numarayla işaretli. Saat ekseni TSİ'dir.
- **Grafikteki gün** — o gün adımların her birinin saati ve fiyatı.

Örnek günler, kuralın bütün adımları (hedef dahil) görünsün diye **kazanan** işlemlerden seçildi. Kuralın ortalama sonucu
grafiğin alt yazısında yazılı ve neredeyse hepsinde eksi; örnek bir başarı öyküsü değil, uygulamanın resmi.

Üç ortak kural her strateji için geçerli:

- **Kapanışı bekle.** "Aralığın dışında" demek mumun dışarıda *kapanması* demektir; mum açıkken çizginin ötesine geçmek
  sinyal değildir. Giriş, sinyal mumu kapanır kapanmaz yapılır.
- **Günde tek işlem.** Kural o gün bir kez tetiklendiyse aynı gün ikinci sinyal alınmaz.
- **Gün sonu.** Açık pozisyon en geç New York gününün sonunda ({{! gun_sonu_tsi }}) kapatılır.

Bütün kurallarda mumlar varsayılan olarak 15 dakikalıktır; farklı olanlar adımlarda yazılı. Fiyat orta fiyattır;
gerçek işlem makas ve kaymayla yapılır.

## Kırılım kuralları

### Londra açılış aralığı kırılımı (ORB)

1. **Aralığı işaretle.** Londra açılışından sonraki ilk 15 dakikalık mumun ({{! tsi "" "Londra 08:00–08:15" }}) en
   yükseğine ve en düşüğüne iki çizgi çek.
2. **Kapanışı bekle, gir.** Sonraki mumlardan biri üst çizginin üstünde kapanırsa al, alt çizginin altında kapanırsa
   sat. Stop aralığın öbür ucuna. Son giriş {{! tsi "" "Londra 12:00" }}; o saate kadar sinyal yoksa o gün işlem yok.
3. **Çık.** Hedef yok: pozisyon stop gelmezse gün sonunda kapanır.

{{! sekil nasil-orb "Adım adım — Londra ORB" }}

{{! nasil_ornek orb }}

### Asya aralığı kırılımı

1. **Aralığı işaretle.** Asya seansının ({{! tsi "" "Londra 00:00–08:00" }}) en yükseği ve en düşüğü aralıktır.
2. **Kapanışı bekle, gir.** Londra açılışından sonra aralığın dışında kapanan ilk mumun yönünde gir. Stop aralığın
   ortasına. Son giriş {{! tsi "" "Londra 11:00" }}.
3. **Çık.** Hedef 1R: girişten stop kadar uzakta. Stop ya da hedef, hangisi önce gelirse.

{{! sekil nasil-asya "Adım adım — Asya aralığı" }}

{{! nasil_ornek asya }}

### New York sabah aralığı kırılımı

1. **Aralığı işaretle.** New York'ta sabahın ilk saatinin ({{! tsi "" "New York 08:00–09:00" }}) en yükseği ve en düşüğü.
2. **Kapanışı bekle, gir.** Aralığın dışında kapanan ilk mumun yönünde gir. Stop aralığın öbür ucuna. Son giriş
   {{! tsi "" "New York 12:00" }}.
3. **Çık.** Hedef yok: stop gelmezse gün sonunda kapanır.

{{! sekil nasil-nyib_0800 "Adım adım — New York sabah aralığı" }}

{{! nasil_ornek nyib_0800 }}

### New York hisse açılışı aralığı kırılımı

1. **Aralığı işaretle.** Hisse piyasası açılışından sonraki ilk saatin ({{! tsi "" "New York 09:30–10:30" }}) en yükseği
   ve en düşüğü.
2. **Kapanışı bekle, gir.** Aralığın dışında kapanan ilk mumun yönünde gir. Stop aralığın öbür ucuna. Son giriş
   {{! tsi "" "New York 12:00" }}.
3. **Çık.** Hedef yok: stop gelmezse gün sonunda kapanır.

{{! sekil nasil-nyib_0930 "Adım adım — New York hisse açılışı aralığı" }}

{{! nasil_ornek nyib_0930 }}

### İç mum kırılımı

1. **Ana mumu işaretle.** Bir mum, bir öncekinin (ana mum) tamamen içinde kaldıysa iç mumdur; ana mumun tepesine ve
   dibine çizgi çek. Yalnız Londra açılışından New York öğlesine kadar ({{! tsi "→" "Londra 08:00" "New York 12:00" }}).
2. **Kapanışı bekle, gir.** Sonraki üç mumdan biri ana mumun dışında kapanırsa o yönde gir; kapanmazsa kurulum iptal.
   Stop ana mumun öbür ucuna.
3. **Çık.** Hedef 2R: girişten stopun iki katı uzakta.

{{! sekil nasil-icmum "Adım adım — İç mum" }}

{{! nasil_ornek icmum }}

### Sıkışma kırılımı

1. **Sıkışmayı bul.** Bollinger bantlarının ikisi de Keltner kanalının içine girdiyse piyasa sıkışmıştır. Bu en az altı
   mum sürdüyse, sıkışma mumlarının en yükseği ile en düşüğü "kutu"dur.
2. **Kapanışı bekle, gir.** Sıkışma bittikten sonraki beş mum içinde kutunun dışında kapanan ilk mumun yönünde gir. Stop
   kutunun öbür ucuna. Son sinyal {{! tsi "" "New York 16:00" }}.
3. **Çık.** Hedef 2R.

{{! sekil nasil-sikisma "Adım adım — Sıkışma" }}

{{! nasil_ornek sikisma }}

### Önceki günün tepe ve dibinin kırılımı

1. **Seviyeleri işaretle.** Bir önceki FX gününün (her gün {{! tsi "" "New York 17:00" }} başlar) en yükseği ve en düşüğü.
2. **Kapanışı bekle, gir.** Londra açılışından sonra bu seviyelerden birini kesen ilk kapanışın yönünde gir (önceki mum
   içeride, bu mum dışarıda kapanmalı). Stop sinyal mumunun öbür ucuna. Son giriş {{! tsi "" "New York 14:00" }}.
3. **Çık.** Hedef 2R.

{{! sekil nasil-pdhl "Adım adım — Önceki günün tepe ve dibi" }}

{{! nasil_ornek pdhl }}

### Pivot kırılımı

1. **Seviyeleri hesapla.** Önceki günün yüksek (Y), düşük (D) ve kapanışından (K): P = (Y + D + K) / 3, R1 = 2P − D,
   S1 = 2P − Y.
2. **Kapanışı bekle, gir.** Bir mum R1'i yukarı ya da S1'i aşağı keserek kapanırsa o yönde gir. Stop sinyal mumunun öbür
   ucuna. Pencere {{! tsi "→" "Londra 08:00" "New York 14:00" }}.
3. **Çık.** Hedef 2R.

{{! sekil nasil-pivot_kirilim "Adım adım — Pivot kırılımı" }}

{{! nasil_ornek pivot_kirilim }}

## Dönüş kuralları

### Açılış aralığının sahte kırılımı

1. **Aralığı işaretle.** Londra açılışının ilk 15 dakikası ({{! tsi "" "Londra 08:00–08:15" }}), ORB'deki gibi.
2. **Sahte kırılımı bekle, ters gir.** Bir mum aralığın dışında kapanır, ardından sonraki iki mumdan biri yeniden
   içeride kapanırsa kırılımın **tersine** gir. Stop sahte kırılımın en uç noktasına. Son giriş
   {{! tsi "" "Londra 14:00" }}.
3. **Çık.** Hedef 1R.

{{! sekil nasil-sahte_orb "Adım adım — Açılış aralığının sahte kırılımı" }}

{{! nasil_ornek sahte_orb }}

### Asya aralığının sahte kırılımı

1. **Aralığı işaretle.** Asya aralığı ({{! tsi "" "Londra 00:00–08:00" }}).
2. **Sahte kırılımı bekle, ters gir.** Aynı kural: dışarıda kapanış, sonraki iki mumdan birinde içeride kapanış →
   ters yönde giriş. Stop sahte kırılımın uç noktasına. Son giriş {{! tsi "" "Londra 14:00" }}.
3. **Çık.** Hedef 1R.

{{! sekil nasil-sahte_asya "Adım adım — Asya aralığının sahte kırılımı" }}

{{! nasil_ornek sahte_asya }}

### Önceki günün tepe ve dibinin sahte kırılımı

1. **Seviyeleri işaretle.** Önceki FX gününün en yükseği ve en düşüğü.
2. **Sahte kırılımı bekle, ters gir.** Seviyenin dışında kapanış, sonraki iki mumdan birinde geri içeride kapanış →
   ters yönde giriş. Stop sahte kırılımın uç noktasına. Pencere
   {{! tsi "→" "Londra 08:00" "New York 14:00" }}.
3. **Çık.** Hedef 1R.

{{! sekil nasil-sahte_pdhl "Adım adım — Önceki günün tepe ve dibinin sahte kırılımı" }}

{{! nasil_ornek sahte_pdhl }}

### VWAP'a dönüş

1. **VWAP'ı ve bandını çiz.** VWAP Londra açılışından beri hacim ağırlıklı ortalama fiyattır; bant VWAP'ın iki standart
   sapma üstü ve altı. İlk saat sinyal alınmaz.
2. **Banda geri dönüşü bekle, gir.** Fiyat bandın dışına çıkıp yeniden bandın içinde kapanırsa VWAP yönünde gir. Stop
   bant dışındaki gezintinin en uç noktasına. Son sinyal {{! tsi "" "New York 16:00" }}.
3. **Çık.** Hedef VWAP: sinyal anındaki VWAP seviyesi.

{{! sekil nasil-vwap_donus "Adım adım — VWAP'a dönüş" }}

{{! nasil_ornek vwap_donus }}

### Pivottan dönüş

1. **Seviyeleri hesapla.** P, R1 ve S1, pivot kırılımındaki gibi.
2. **Değip dönmesini bekle, gir.** Fiyat R1'e değip altında kapanırsa sat; S1'e değip üstünde kapanırsa al. Stop sinyal
   mumunun seviyenin ötesindeki ucuna. Pencere {{! tsi "→" "Londra 08:00" "New York 14:00" }}.
3. **Çık.** Hedef pivot (P).

{{! sekil nasil-pivot_donus "Adım adım — Pivottan dönüş" }}

{{! nasil_ornek pivot_donus }}

### Fiksing sonrası dönüş

1. **Fiksinge giden mumu oku, ters gir.** Londra fiksinginden ({{! tsi "" "Londra 16:00" }}) önceki son 15 dakikalık mum
   yükselerek kapandıysa fiksingde sat, düşerek kapandıysa al.
2. **Çık.** Stop ve hedef yok: iki mum, yani 30 dakika sonra çık.

{{! sekil nasil-fiks_donus "Adım adım — Fiksing sonrası dönüş" }}

{{! nasil_ornek fiks_donus }}

## Akış kuralları

### Fiksing momentumu

1. **Fiksingden önceki mumu oku, aynı yönde gir.** Fiksingden önceki 5 dakikalık mum
   ({{! tsi "" "Londra 15:50–15:55" }}) yükselerek kapandıysa al, düşerek kapandıysa sat; giriş o mum kapanınca.
2. **Çık.** Stop ve hedef yok: tam fiksingde ({{! tsi "" "Londra 16:00" }}) çık.

{{! sekil nasil-fiks_momentum "Adım adım — Fiksing momentumu" }}

{{! nasil_ornek fiks_momentum }}

### Londra açılışından New York öğleden sonrasına momentum

1. **Londra'nın ilk saatini oku.** {{! tsi "" "Londra 08:00–09:00" }} arasındaki 60 dakikalık mum yükselerek kapandıysa
   yön alış, düşerek kapandıysa satıştır.
2. **Öğlen gir.** O yönde {{! tsi "" "New York 12:00" }} gir.
3. **Çık.** Stop ve hedef yok: {{! tsi "" "New York 16:00" }} çık.

{{! sekil nasil-momentum "Adım adım — Gün içi momentum" }}

{{! nasil_ornek momentum }}

### VWAP geri çekilmesi

1. **Trendi bul, geri çekilmeyi bekle, gir.** Son 12 mumun hepsi VWAP'ın aynı yanında kapandıysa trend var. Fiyat VWAP'a
   değip trend yönünde kapanırsa trend yönünde gir. Stop sinyal mumunun öbür ucuna. VWAP Londra açılışından
   hesaplanır; ilk saat sinyal alınmaz, son sinyal {{! tsi "" "New York 16:00" }}.
2. **Çık.** Hedef 2R.

{{! sekil nasil-vwap_cekilme "Adım adım — VWAP geri çekilmesi" }}

{{! nasil_ornek vwap_cekilme }}

## Haber kuralları

Haber kurallarında mumlar 5 dakikalıktır ve açıklama anına hizalıdır: "ilk haber mumu" açıklamanın olduğu dakikada açılan
mumdur. Sınanan olaylar ABD tarım dışı istihdam ve enflasyon verisi, Fed kararı ve basın toplantısı, Avrupa Merkez
Bankası (EUR/USD) ve İngiltere Merkez Bankası (GBP/USD) kararlarıdır; saatleri takvimden alınır.

### Haber kırılımı (N1)

1. **İlk haber mumunu bekle, aynı yönde gir.** İlk haber mumu yükselerek kapandıysa al, düşerek kapandıysa sat; giriş o
   mum kapanınca. Stop ilk haber mumunun öbür ucuna.
2. **Çık.** Hedef 1R.

{{! sekil nasil-n1 "Adım adım — Haber kırılımı" }}

{{! nasil_ornek n1 }}

### Haber fade'i (N2)

1. **Büyük hareketi ve dönüşü bekle, ters gir.** İlk haber mumu olağan oynaklığın (ATR) iki katından fazla hareket
   ettiyse, sonraki üç mumdan biri ters yönde kapandığında hareketin tersine gir. Stop o ana kadarki hareketin ucuna.
2. **Çık.** Hedef haberden önceki fiyat.

{{! sekil nasil-n2 "Adım adım — Haber fade'i" }}

{{! nasil_ornek n2 }}

### Haber öncesi aralığın kırılımı — straddle (N3)

1. **Aralığı işaretle.** Haberden önceki altı mumun (yarım saat) en yükseği ve en düşüğü.
2. **Kapanışı bekle, gir.** Haberden sonra aralığın dışında kapanan ilk mumun yönünde gir (en geç altıncı mumda). Stop
   aralığın öbür ucuna.
3. **Çık.** Hedef 1R.

{{! sekil nasil-n3 "Adım adım — Straddle" }}

{{! nasil_ornek n3 }}

### Başarısız haber kırılımı (N4)

1. **Aralığı işaretle.** Haberden önceki altı mumun en yükseği ve en düşüğü.
2. **Geri dönüşü bekle, ters gir.** İlk haber mumu aralığın dışında kapanır, ikinci mum yeniden içeride kapanırsa ilk
   hareketin tersine gir. Stop ilk iki mumun ucuna.
3. **Çık.** Hedef aralığın öbür ucu.

{{! sekil nasil-n4 "Adım adım — Başarısız haber kırılımı" }}

{{! nasil_ornek n4 }}

### Geri çekilme sonrası devam (N5)

1. **İtkiyi ve geri çekilmeyi bekle, gir.** İlk haber mumu en az yarım ATR hareket ettiyse, sonraki altı mum içinde
   fiyatın bu hareketin yarısını geri vermesini bekle; ardından ilk hareket yönünde kapanan ilk mumda gir. Stop geri
   çekilmenin ucuna.
2. **Çık.** Hedef ilk haber mumunun ucu.

{{! sekil nasil-n5 "Adım adım — Geri çekilme sonrası devam" }}

{{! nasil_ornek n5 }}

## Bu dersten sonra

Kuralların her birinin nasıl uygulandığını gördünüz. Sonraki üç ders aynı kuralların backtest sonucunu verir ve stop ile
hedef başka yere konsaydı ne değişeceğini gösterir.
