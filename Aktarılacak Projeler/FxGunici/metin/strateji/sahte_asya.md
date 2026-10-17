### Ne

Aynı başarısız kırılım kuralı, seviye olarak **Asya aralığıyla** (Londra 00:00 → 08:00): Londra açıldıktan sonra
fiyat gecenin aralığının dışında kapanır, bir ya da iki mum içinde kırılan kenarın berisine dönerse ters yönde
girilir.
Kırılım dersindeki Asya aralığı kuralının aynasıdır.

### Piyasa mantığı

Asya aralığı geceden kalan stop emirlerinin haritasıdır: gece pozisyon taşıyan herkes stopunu gecenin tepesinin
üstüne ya da dibinin altına koyar. Londra'nın ilk saatinde bu uçların sınanması, Avrupa masalarının o likiditeyi
kullanmasıdır; yeni bir bilgi yoksa fiyat aralığa geri döner. Asya aralığının ORB'den farkı genişliğidir: sekiz
saatlik aralığın uçları açılıştaki fiyattan uzak olabilir ve o uçlara gün içinde hiç uzanılmayabilir.

### Kurallar

- **Seviye.** Londra 00:00 → 08:00 arasındaki 1 dakikalık orta fiyatların en yükseği ve en düşüğü (TSİ'de
  İngiltere yaz saatindeyken 02:00 → 10:00, kış saatindeyken 03:00 → 11:00).
- **Kırılım, geri dönüş, stop.** Sahte ORB ile aynı: dışarıda kapanış, en çok "pencere" kadar mum içinde kırılan
  kenarın berisinde kapanış (karşı kenarın ötesindeki kapanış dahil), stop gezintinin ucunda.
- **Pencere.** Londra 08:00 → 14:00 ({{! tsi "→" "Londra 08:00" "Londra 14:00" }}); gün başına tek işlem.

{{! kural }}

Varsayılan: 15 dakikalık mumlar, iki mumluk pencere, 1R hedef.{{? B.varsayilan.tf == 15 and B.varsayilan.pencere == 2 and B.varsayilan.seviye == "asya" and B.varsayilan.hedef == "1R" and B.varsayilan.stop_turu == "sert" }}

### Örnekler

{{! sekil ornek "Örnek günler — Sahte Asya" }}

{{! ornek }}

Noktalı mavi çizgiler gecenin aralığı (Londra 00:00'dan başlar), mavi bant aralığa geri dönen sinyal mumudur. Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip zararla kapanan işlemdir: {{! tuzak "geri dönüş başlıyor, sonra kırılım yeniden başlayıp stopu alıyor." "geri dönüş başlıyor ama sürmüyor; işlem stopa değmeden zararla kapanıyor ({cikis})." }}

### Sonuçlar

{{! sonuclar }}

**Ön kaydın harfiyle.** Sahte ORB'deki iki okuma burada da geçerli; ikisi de ilk sonuçlardan önce sabitlendi ve
hüküm onlarla verilir. Kırılım mumu: ön kayıt kırılımı "bir mum seviyenin dışında kapanır" diye tanımlar ve önceki
kapanışı sormaz; bu ölçüm seviyeyi kesen mumu arar. Gecenin aralığında iki okuma tanım gereği aynıdır: pencerenin
ilk mumundan önceki kapanış gecenin son fiyatıdır, yani aralığın içindedir. Aynı koşuda ayrıca ölçüldü: dört
paritede ızgaranın hiçbir kombinasyonunda tek bir işlem değişmez.{{? E.yorum.acilis.degisen == 0 and G.yorum.acilis.degisen == 0 and J.yorum.acilis.degisen == 0 and A.yorum.acilis.degisen == 0 }}
Geri dönüş: harfe göre dönüş mumu gecenin aralığının içinde kapanır ve karşı kenarın ötesinde kapanan mum ters
yönde yeni bir kırılımdır; bu ölçüm yalnız kırılan kenarı sorar. Harfin iki okuması aynı koşuda ayrıca, her biri
tek başına ölçüldü. {{! yorum_cumle }}

{{! yorum }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Gece aralığı.** Londra 00:00 → 08:00 ({{! tsi "→" "Londra 00:00" "Londra 08:00" }}) tepe ve dip.
4. **Kırılımı gör, girme; geri dönüşü bekle.** En çok iki mum içinde kırılan kenarın berisinde kapanış.
5. **Stop gezintinin ucunda, hedef 1R.** Pencere Londra 14:00'te kapanır (TSİ 16:00 ya da 17:00).
6. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
