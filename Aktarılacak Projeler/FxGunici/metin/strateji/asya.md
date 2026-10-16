### Ne

Asya seansının (Londra gece yarısından Londra açılışına kadar) tepesi ve dibi bir aralık tanımlar. Londra
açıldıktan sonra fiyat bu aralığın dışında kapanırsa kırılım yönünde işleme girilir. Kural Londra açılış
aralığı kırılımının daha uzun pencereli kardeşidir: tek bir mumun değil, yedi ya da sekiz saatin aralığı.

### Piyasa mantığı

Asya seansında EUR/USD ve GBP/USD'de işlem hacmi Londra ve New York'un altındadır ve fiyat genellikle günün
geri kalanından dar bir bantta kalır. Bu bant, gece boyunca kimsenin üzerinde anlaşamadığı bir denge gibi
okunur; Avrupa masaları açıldığında yeni bilgiyle bu denge bozulur ve kırılan yön günün yönü olur — savunusu
bu. Karşı savunu da aynı yerden gelir: bandın iki ucu, gece boyunca konmuş stop emirlerinin en yoğun olduğu
yerdir ve Londra'nın ilk hareketi çoğu zaman o stop'ları alıp bandın içine geri döner (fade dersindeki "sahte
Asya" kuralı tam bunu ölçer). USD/JPY ve AUD/USD için Asya saatleri "sakin seans" değildir: Tokyo ve Sidney o
saatlerde açıktır ve bu iki paritede Asya aralığı gerçek bir seansın aralığıdır.

### Kurallar

- **Aralık.** Londra 00:00'dan aralık sonuna (07:00 ya da 08:00) kadar 1 dakikalık orta fiyatın en
  yükseği ve en düşüğü. TSİ'de Londra 00:00, İngiltere yaz saatindeyken 02:00, kış saatindeyken 03:00'tür.
- **Sinyal.** Londra 08:00'den sonra aralığın dışında kapanan ilk mum; gün başına tek işlem.
- **Giriş, stop, hedef.** Giriş sonraki dakikanın açılışında yürütülebilir fiyattan; stop aralığın ortası
  ya da karşı ucu; hedef 1R, 2R ya da gün sonu.
- **Son giriş.** Londra 11:00 ya da 14:00.

{{! kural }}

Varsayılan aralığı Londra açılışında kapatır, 15 dakikalık mumla kırılımı arar, stop'u aralığın ortasına
koyar ve 1R hedefler; son giriş Londra 11:00.{{? B.varsayilan.tf == 15 and B.varsayilan.aralik_sonu_londra == "08:00" and B.varsayilan.stop_yeri == "orta" and B.varsayilan.hedef == "1R" and B.varsayilan.son_giris_londra == "11:00" }}
Ortadaki stop bir tercihtir: Asya aralığı sekiz saatin aralığıdır ve açılışın tek mumundan geniştir; karşı
uçtaki stop riski aralığın tamamı kadar büyütür. Orta, kırılımın geri dönüp aralığın yarısını geçmesini
"fikir bozuldu" sayar.

### Örnekler

{{! sekil ornek "Örnek günler — Asya aralığı" }}

{{! ornek }}

Asya aralığı figürde iki noktalı mavi çizgidir. Aralık gece boyunca oluştuğu için Londra açıldığında sinyal
çoğu zaman ilk mumlarda gelir; açılıştan önce kırılmış bir aralık da Londra 08:00'den sonraki ilk dışarıda
kapanışta sinyal üretir. Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlemdir; tuzak örneği
önce lehine en az yarım R gidip sonra zararla kapanan işlem, yani kırılımın aralığa geri döndüğü gün.

### Sonuçlar

{{! sonuclar }}

### Koşullar

{{! kosullar }}

Asya aralığının genişliği (aralık / günlük ATR) bu kuralın en doğal koşuludur ve iki yönlü okunabilir: dar
bir gece sıkışmış bir dengeyi, geniş bir gece hareketin açılıştan önce yaşanmış olabileceğini anlatır. Bu
kuralda "aralık" ile "Asya aralığı" aynı ölçüdür ve tek değişken sayılır.{{? E.varsayilan.kosul[1].degisken == "asya_atr" and E.varsayilan.kosul[1].hukum == "esdeger" and G.varsayilan.kosul[1].hukum == "esdeger" and J.varsayilan.kosul[1].hukum == "esdeger" and A.varsayilan.kosul[1].hukum == "esdeger" }} Ölçüm: {{! kosul_tek range_atr }}.

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Saat.** Aralık Londra 00:00 → 08:00: TSİ 02:00 → 10:00 (İngiltere yaz saati) ya da 03:00 → 11:00 (kış
   saati). Son giriş Londra 11:00: TSİ 13:00 ya da 14:00.
4. **Aralığı işaretle.** Gece boyunca en yüksek ve en düşük orta fiyat.
5. **Kapanışı bekle.** Londra açıldıktan sonra aralığın dışında kapanan ilk mum.
6. **Stop aralığın ortasında.** Risk = giriş fiyatı ile orta arasındaki uzaklık; hedef bunun bir katı.
7. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
