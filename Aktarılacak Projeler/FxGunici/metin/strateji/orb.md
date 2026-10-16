### Ne

Londra açılışında oluşan ilk mumun tepesi ve dibi bir **açılış aralığı** tanımlar. Fiyat bu aralığın
dışında kapanırsa kırılım yönünde işleme girilir: aralığın üstünde kapanış alış, altında kapanış satış.
Kural vadeli piyasalarda Toby Crabel'in açılış aralığı kırılımı (*opening range breakout*, ORB)
çalışmalarıyla yaygınlaştı; FX'te "açılış" bir borsa çanı değil, likiditenin el değiştirdiği bir saattir:
Londra 08:00.

### Piyasa mantığı

FX yirmi dört saat işler ama likidite eşit dağılmaz. Asya seansında dar bir aralıkta biriken emirler —
kurumsal akış, opsiyon bariyerlerinin hedge'i, gece boyunca konmuş stop'lar — Avrupa masaları açıldığında
işlenir. Kırılımı savunan görüş şöyle der: açılışın ilk mumu bu birikimin hangi yöne boşaldığını gösterir ve
bilgili akış o yönde sürer. Karşı görüş de aynı gözlemden çıkar: açılıştaki ilk hareket çoğu zaman likidite
toplamaktır, aralığın hemen dışındaki stop'lar alınır ve fiyat geri döner. Bu dersin işi hangisinin daha sık
olduğunu ölçmek. İkinci görüşün kuralı (**başarısız kırılım**) fade dersinde aynı aralıkla ayrıca sınanıyor.

### Kurallar

- **Aralık.** Londra 08:00'den itibaren ilk mum (15 dakikalık mumda 08:00–08:15, 60 dakikalıkta
  08:00–09:00). TSİ'de bu saat yaz saatinde 10:00, kışın 11:00'dir; Avrupa ile ABD'nin saat değiştirdiği ara
  haftalarda Londra saati değişmediği için TSİ karşılığı da değişmez.
- **Sinyal.** Aralıktan sonraki mumlardan, aralığın **dışında kapanan** ilk mum; yön kapanışın tarafı. Gün
  başına tek işlem.
- **Giriş.** Sinyal mumu kapanınca, sonraki dakikanın açılışında, yürütülebilir fiyattan (alışta ask,
  satışta bid).
- **Stop.** Aralığın karşı ucu (ya da ortası); sert stop emir tarafında dakika dakika izlenir.
- **Hedef.** 1R, 2R ya da gün sonu (16:55 New York; TSİ yazın 23:55, kışın 00:55).
- **Son giriş.** Sinyal mumunun kapanışı en geç Londra saatiyle "son giriş"; sonrası işlem yok.

Önceden kaydın ızgarası ve veriye bakmadan seçilmiş varsayılan:

{{! kural }}

Varsayılan, kuralın ders kitabı hâlidir: 15 dakikalık aralık, karşı uçta sert stop, kârı gün sonuna kadar
bırakmak.{{? B.varsayilan.tf == 15 and B.varsayilan.stop_yeri == "karsi_uc" and B.varsayilan.stop_turu == "sert" and B.varsayilan.hedef == "gun_sonu" and B.varsayilan.son_giris_londra == "12:00" }} Kârın koşmasına izin vermek açılış kırılımının asıl iddiasıdır; 1R ya da 2R hedefler o iddianın daha
temkinli biçimleridir ve ızgarada ayrıca ölçülür.

### Örnekler

{{! sekil ornek "Örnek günler — Londra ORB" }}

{{! ornek }}

Figürde mavi noktalı çizgiler aralığın iki ucu, kırmızı çizgi stop, üçgen yürütülen giriş fiyatıdır. Kazanan
örnek kuralın vaat ettiği günü gösterir: aralık kırılıyor ve hareket gün boyu sürüyor. Kaybeden örnek kuralın
asıl maliyetini gösterir: kırılım kapanışla teyit edildiği hâlde fiyat aralığa geri dönüyor ve karşı uçtaki
stop alınıyor. Her iki örnek de örneklem dışının en son kazanan ve en son kaybeden işlemidir; seçim kuralı
sonuçtan önce yazıldı, figür "en güzel günü" göstermiyor.

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

Kuralın kendisi bir şey kazandırmasa da belirli günlerde kazandırıyor olabilir. Bu bölüm girişin olduğu anda
bilinen on dört değişkeni{{? len(ON.kosul.degiskenler) == 14 }} (aralığın günlük ATR'ye oranı, önceki günün yönü, oynaklık yüzdeliği, haftanın günü,
büyük olay günü, saat değişimi haftası…) kovalara ayırır. Seçim yalnız örneklem içinde yapılır; örneklem dışı
yalnız sınar.

{{! kosullar }}

Tutan bir koşul, kuralı "o günlerde çalışan bir kural" yapmaz: on dört değişkenin her biri ayrı bir denemedir
ve şansla birkaçının tutması beklenir. Koşul, kontrol listesine ancak öbür paritelerde de aynı yönde
duruyorsa bir aday olarak girer.

### Kontrol listesi

1. **Saat.** Aralık Londra 08:00'de başlar: TSİ 10:00 (yaz) ya da 11:00 (kış). Son giriş Londra 12:00:
   TSİ 14:00 ya da 15:00.
2. **Aralığı işaretle.** İlk mumun tepe ve dibi; mum kapanmadan aralık yoktur.
3. **Kapanışı bekle.** Mumun aralığın dışına taşması sinyal değildir; dışarıda kapanması sinyaldir. Giriş
   bir sonraki dakikada.
4. **Stop karşı uçta, emir girişle birlikte.** Stop'un uzaklığı riskin kendisidir; pozisyon büyüklüğü bu
   uzaklıktan kurulur (1R = hesap riskinin sabit bir payı).
5. **Gün sonunda kapat.** 16:55 New York.
6. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
