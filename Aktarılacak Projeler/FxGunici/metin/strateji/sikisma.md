### Ne

Oynaklık dalgalanır: sakin dönemleri hareketli dönemler izler. **Sıkışma** (*squeeze*) kuralı kapanışların
dağılımının mumların kendi büyüklüğüne göre olağandışı daraldığı anı ölçer ve dağılım yeniden açıldığında
oluşan yöne girer. Ölçü iki bandın karşılaştırmasıdır: **Bollinger
bantları** (kapanışların standart sapmasıyla genişler) **Keltner kanalının** (ortalama gerçek aralıkla genişler)
içine girdiğinde fiyatın son mumlardaki dağılımı mumların kendi büyüklüğüne göre olağandışı dardır. John
Carter'ın "TTM Squeeze" adıyla yaygınlaştırdığı tanım budur.

### Piyasa mantığı

Bollinger bandı kapanışların birbirinden ne kadar uzaklaştığını, Keltner kanalı mumların ne kadar uzun olduğunu
ölçer. Mumlar kısalmadığı hâlde kapanışlar dar bir bölgede toplanıyorsa piyasa yön bulamıyor demektir, ama
durgun olduğu söylenemez; kırılım savunusu, bu dengenin bozulduğu anda biriken pozisyonların tek yöne kapanacağını söyler.
Kuralın zayıf noktası zamanlamadır: sıkışmanın bittiğini söyleyen şey bandın genişlemesidir ve bant ancak hareket
başladıktan sonra genişler; girişin ne kadarının hareketin başında, ne kadarının ortasında olduğu ölçülmeden
bilinemez.

### Kurallar

- **Bollinger.** 20 mumun kapanış ortalaması ± 2 standart sapma (kapanışlar, anakütle standart sapması).
- **Keltner.** 20 mumluk üstel ortalama ± {{= "1,5" }} × ATR(20) (Wilder).
- **Sıkışma.** Bollinger'ın iki bandı da Keltner'ın içinde. En az "süre" kadar ardışık sıkışma mumu gerekir; sıkışma,
  sıkışmasız ilk mumda biter.
- **Kutu.** Sıkışma mumlarının en yüksek tepesi ve en düşük dibi.
- **Yön.** "Kutu kırılımı": sıkışma bittikten sonraki beş mumun içinde kutunun dışında kapanan ilk mum. "TTM
  momentumu": sıkışmanın bittiği mumun kapanışı 20 mumluk ortalamanın üstündeyse alış, altındaysa satış — Carter'ın
  momentum göstergesinin yerine konmuş basit bir vekildir, göstergenin kendisi değil.
- **Stop.** Kutunun karşı ucu ya da ortası. Sinyal mumu en geç 16:00 New York'ta ({{! tsi "" "New York 16:00" }}) kapanır.
- **Hedef.** 1R, 2R ya da zaman ({{ ON.genel.desen_zaman_mum | n }} mum).

{{! kural }}

Varsayılan en az altı sıkışma mumu ister, kutu kırılımıyla girer, stopu kutunun karşı ucuna koyar ve 2R
hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.sure == 6 and B.varsayilan.yon == "kutu" and B.varsayilan.stop_yeri == "karsi_uc" and B.varsayilan.hedef == "2R" and B.varsayilan.stop_turu == "sert" }} Sıkışma gece seansında da oluşabilir; mumlar FX işlem gününe göre gruplanmaz, yalnız sinyal mumunun
günü ve saati sınanır.

### Örnekler

{{! sekil ornek "Örnek günler — Sıkışma" }}

{{! ornek }}

Figürde turuncu çizgiler Bollinger bandı, kesikli gri çizgiler Keltner kanalıdır; turuncu gölge sıkışma
mumlarıdır (Bollinger'in iki bandı da Keltner'in içinde). Noktalı mavi çizgiler sıkışma kutusunun iki ucu (kutunun
içinde kalan son kesintisiz mumlardan başlar), mavi bant sinyal mumudur. Kutu birkaç saatlik bir
dengeyi özetler; uzun bir sıkışmanın kutusu da büyüktür ve stopu uzaklaştırır. Sıkışma gün içinde birden çok
kez oluşabilir: {{! gun_ici }}. Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği
önce lehine en az yarım R gidip zararla kapanan işlemdir.

### Sonuçlar

{{! sonuclar }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Sıkışmayı say.** Bollinger'ın iki bandı da Keltner'ın içinde; en az altı mum üst üste.
4. **Kutuyu işaretle.** Sıkışma mumlarının en yüksek ve en düşük noktası.
5. **Kapanışı bekle.** Sıkışma bittikten sonraki beş mum içinde kutunun dışında kapanış; gelmezse desen bitti.
6. **Stop kutunun karşı ucunda, hedef 2R.** Sinyal en geç 16:00 New York (TSİ 23:00 ya da 00:00, ABD'nin
   saatine göre).
7. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
