### Ne

Oynaklık dalgalanır: sakin dönemleri hareketli dönemler izler. **Sıkışma** (*squeeze*) kuralı bu dalgalanmanın
dibini ölçer ve oynaklık geri döndüğünde açılan yöne girer. Ölçü iki bandın karşılaştırmasıdır: **Bollinger
bantları** (kapanışların standart sapmasıyla genişler) **Keltner kanalının** (ortalama gerçek aralıkla genişler)
içine girdiğinde fiyatın son mumlardaki dağılımı mumların kendi büyüklüğüne göre olağandışı dardır. John
Carter'ın "TTM Squeeze" adıyla yaygınlaştırdığı tanım budur.

### Piyasa mantığı

Bollinger bandı kapanışların birbirinden ne kadar uzaklaştığını, Keltner kanalı mumların ne kadar uzun olduğunu
ölçer. Mumlar uzun kaldığı hâlde kapanışlar dar bir bölgede toplanıyorsa piyasa yön bulamıyor ama durgun da
değildir; kırılım savunusu, bu dengenin bozulduğu anda biriken pozisyonların tek yöne kapanacağını söyler.
Kuralın zayıf noktası zamanlamadır: sıkışmanın bittiğini söyleyen şey bandın genişlemesidir ve bant ancak hareket
başladıktan sonra genişler; girişin ne kadarının hareketin başında, ne kadarının ortasında olduğu ölçülmeden
bilinemez.

### Kurallar

- **Bollinger.** 20 mumun kapanış ortalaması ± 2 standart sapma (kapanışlar, nüfus sapması).
- **Keltner.** 20 mumluk üstel ortalama ± {{= "1,5" }} × ATR(20) (Wilder).
- **Sıkışma.** Bollinger'ın iki bandı da Keltner'ın içinde. En az "süre" kadar ardışık sıkışma mumu gerekir; sıkışma,
  sıkışmasız ilk mumda biter.
- **Kutu.** Sıkışma mumlarının en yüksek tepesi ve en düşük dibi.
- **Yön.** "Kutu kırılımı": sıkışma bittikten sonraki beş mumun içinde kutunun dışında kapanan ilk mum. "TTM
  momentumu": sıkışmanın bittiği mumun kapanışı 20 mumluk ortalamanın üstündeyse alış, altındaysa satış — Carter'ın
  momentum göstergesinin yerine konmuş basit bir vekildir, göstergenin kendisi değil.
- **Stop.** Kutunun karşı ucu ya da ortası. Sinyal mumu en geç 16:00 New York'ta kapanır.

{{! kural }}

Varsayılan en az altı sıkışma mumu ister, kutu kırılımıyla girer, stop'u kutunun karşı ucuna koyar ve 2R
hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.sure == 6 and B.varsayilan.yon == "kutu" and B.varsayilan.stop_yeri == "karsi_uc" and B.varsayilan.hedef == "2R" and B.varsayilan.stop_turu == "sert" }} Sıkışma gece seansında da oluşabilir; mumlar FX işlem gününe göre gruplanmaz, yalnız sinyal mumunun
günü ve saati sınanır.

### Örnekler

{{! sekil ornek "Örnek günler — Sıkışma" }}

{{! ornek }}

Figürde mavi çizgiler sıkışma kutusunun iki ucudur. Kutu birkaç saatlik bir sakinliği özetler; uzun bir sıkışmanın
kutusu da büyüktür ve stop'u uzaklaştırır.

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Sıkışmayı say.** Bollinger'ın iki bandı da Keltner'ın içinde; en az altı mum üst üste.
2. **Kutuyu işaretle.** Sıkışma mumlarının en yüksek ve en düşük noktası.
3. **Kapanışı bekle.** Sıkışma bittikten sonraki beş mum içinde kutunun dışında kapanış; gelmezse desen bitti.
4. **Stop kutunun karşı ucunda, hedef 2R.** Sinyal en geç 16:00 New York (TSİ 23:00 ya da 00:00).
5. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
