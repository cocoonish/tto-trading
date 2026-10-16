### Ne

Asya seansının (Londra gece yarısından Londra açılışına kadar) tepesi ve dibi bir aralık tanımlar. Londra
açıldıktan sonra fiyat bu aralığın dışında kapanırsa kırılım yönünde işleme girilir. Kural Londra açılış
aralığı kırılımının daha uzun pencereli kardeşidir: tek bir mumun değil, sekiz saatin aralığı.

### Piyasa mantığı

Asya seansında majör paritelerde (USD/JPY ve AUD/USD hariç tutulursa) işlem hacmi düşüktür ve fiyat çoğu gece
dar bir bantta kalır. Bu bant, gece boyunca kimsenin üzerinde anlaşamadığı bir denge gibi okunur; Avrupa
masaları açıldığında yeni bilgiyle bu denge bozulur ve kırılan yön günün yönü olur — savunusu bu. Karşı
savunu da aynı yerden gelir: dar bir bandın iki ucu, gece boyunca konmuş stop emirlerinin en yoğun olduğu
yerdir ve Londra'nın ilk hareketi çoğu zaman o stop'ları alıp bandın içine geri döner (fade dersindeki "sahte
Asya" kuralı tam bunu ölçer). Asya aralığının bir özelliği de USD/JPY ve AUD/USD için "sakin seans" olmamasıdır:
Tokyo ve Sidney o saatlerde açıktır ve bu iki paritede Asya aralığı gerçek bir seansın aralığıdır.

### Kurallar

- **Aralık.** Londra 00:00'dan aralık sonuna (07:00 ya da 08:00) kadar 1 dakikalık orta fiyatın en
  yükseği ve en düşüğü. TSİ'de Londra 00:00 yazın 02:00, kışın 03:00'tür.
- **Sinyal.** Londra 08:00'den sonra aralığın dışında kapanan ilk mum; gün başına tek işlem.
- **Giriş, stop, hedef.** Giriş sonraki dakikanın açılışında yürütülebilir fiyattan; stop aralığın ortası
  ya da karşı ucu; hedef 1R, 2R ya da gün sonu.
- **Son giriş.** Londra 11:00 ya da 14:00.

{{! kural }}

Varsayılan aralığı Londra açılışında kapatır, 15 dakikalık mumla kırılımı arar, stop'u aralığın ortasına
koyar ve 1R hedefler; son giriş Londra 11:00.{{? B.varsayilan.tf == 15 and B.varsayilan.aralik_sonu_londra == "08:00" and B.varsayilan.stop_yeri == "orta" and B.varsayilan.hedef == "1R" and B.varsayilan.son_giris_londra == "11:00" }}
Ortadaki stop bir tercihtir: Asya aralığı çoğu gün geniştir ve karşı uçtaki stop riski açılış aralığının
birkaç katına çıkarır; orta, kırılımın geri dönüp aralığın yarısını geçmesini "fikir bozuldu" sayar.

### Örnekler

{{! sekil ornek "Örnek günler — Asya aralığı" }}

{{! ornek }}

Asya aralığı figürde iki mavi çizgidir. Aralık gece boyunca oluştuğu için Londra açıldığında sinyal çoğu zaman
ilk mumlarda gelir; açılıştan önce kırılmış bir aralık da Londra 08:00'den sonraki ilk kapanışta sinyal
üretir.

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

{{! kosullar }}

Asya aralığının genişliği (aralık / günlük ATR) bu kuralın en doğal koşuludur: dar bir gece, sıkışmış bir
dengeyi; geniş bir gece, kırılımın çoktan gerçekleştiğini anlatır. Tabloda bu değişkenin hükmü ayrıca
okunmalı.

### Kontrol listesi

1. **Saat.** Aralık Londra 00:00 → 08:00: TSİ yazın 02:00 → 10:00, kışın 03:00 → 11:00. Son giriş Londra
   11:00: TSİ 13:00 ya da 14:00.
2. **Aralığı işaretle.** Gece boyunca en yüksek ve en düşük orta fiyat.
3. **Kapanışı bekle.** Londra açıldıktan sonra aralığın dışında kapanan ilk mum.
4. **Stop aralığın ortasında.** Risk = giriş fiyatı ile orta arasındaki uzaklık; hedef bunun bir katı.
5. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
