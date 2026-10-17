### Ne

Londra açılışında oluşan ilk mumun tepesi ve dibi bir **açılış aralığı** tanımlar. Fiyat bu aralığın
dışında kapanırsa kırılım yönünde işleme girilir: aralığın üstünde kapanış alış, altında kapanış satış.
Kural vadeli piyasalarda Toby Crabel'in açılış aralığı kırılımı (*opening range breakout*, ORB)
çalışmalarıyla yaygınlaştı; FX'te "açılış" bir borsa çanı değil, likiditenin el değiştirdiği bir saattir:
Londra 08:00.

### Piyasa mantığı

FX yirmi dört saat işler ama likidite eşit dağılmaz. Asya seansında dar bir aralıkta biriken emirler —
kurumsal akış, opsiyon bariyerlerinin hedge'i, gece boyunca konmuş stoplar — Avrupa masaları açıldığında
işlenir. Kırılımı savunan görüş şöyle der: açılışın ilk mumu bu birikimin hangi yöne boşaldığını gösterir ve
bilgili akış o yönde sürer. Karşı görüş de aynı gözlemden çıkar: açılıştaki ilk hareket çoğu zaman likidite
toplamaktır, aralığın hemen dışındaki stoplar alınır ve fiyat geri döner. Bu dersin işi hangisinin daha sık
olduğunu ölçmek. İkinci görüşün kuralı (**başarısız kırılım**) fade dersinde aynı aralıkla ayrıca sınanıyor.

### Kurallar

- **Aralık.** Londra 08:00'den itibaren ilk mum (15 dakikalık mumda 08:00–08:15, 60 dakikalıkta
  08:00–09:00). Londra açılışının TSİ saati yalnız İngiltere'nin saatine bağlıdır: İngiltere yaz saatindeyken
  10:00, kış saatindeyken 11:00. Mart ve ekim sonu–kasım başındaki ara haftalarda (Avrupa ile ABD'nin saati farklı günlerde
  değiştiği haftalar) İngiltere kış saatindedir, açılış iki ara dönemde de TSİ 11:00'dir.
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
temkinli biçimleridir ve ızgarada ayrıca ölçülür (sonuçlarda "Stop ve hedef" tablosu).

### Örnekler

{{! sekil ornek "Örnek günler — Londra ORB" }}

{{! ornek }}

Figürde noktalı mavi çizgiler açılış aralığının iki ucu (aralığın oluştuğu Londra 08:00 mumundan başlar), mavi bant sinyal mumu, kırmızı çizgi stop, üçgen
yürütülen giriş fiyatıdır. Kazanan örnek kuralın vaat ettiği günü gösterir: kırılım teyit ediliyor ve hareket
sürüyor. Kaybeden örnek, lehine yarım R'ye bile ulaşmadan zararla kapanan işlemdir: kapanışla teyit edilmiş
bir kırılımın arkası gelmiyor. Tuzak örneği kuralın en pahalı biçimini gösterir: işlem önce lehine en az
yarım R gidiyor, sonra fiyat geri dönüp zararla kapatıyor. Kârı gün sonuna bırakan bir kural bu kârı korumaz;
1R ve 2R hedefler ızgarada tam bu yüzden var; etkileri sonuçlardaki "Stop ve hedef" tablosunda.

### Sonuçlar

{{! sonuclar }}

### Koşullar

Kuralın kendisi bir şey kazandırmasa da belirli günlerde kazandırıyor olabilir. Bu bölüm girişin olduğu anda
bilinen on dört değişkeni{{? len(ON.kosul.degiskenler) == 14 }} (aralığın günlük ATR'ye oranı, önceki günün yönü, oynaklık yüzdeliği, haftanın günü,
büyük olay günü, saat değişimi haftası…) kovalara ayırır. Seçim yalnız örneklem içinde yapılır; örneklem dışı
yalnız sınar.

{{! kosullar }}

Açılış aralığının genişliği bu kuralın en doğal koşuludur ve iki yönlü okunabilir: dar bir açılış henüz
boşalmamış bir birikimi, geniş bir açılış hareketin ilk mumda tükendiğini anlatabilir. Ölçüm, aralık / günlük
ATR için: {{! kosul_tek range_atr }}.

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Saat.** Aralık Londra 08:00'de başlar: TSİ 10:00 (İngiltere yaz saati) ya da 11:00 (kış saati). Son
   giriş Londra 12:00: TSİ 14:00 ya da 15:00.
4. **Aralığı işaretle.** İlk mumun tepe ve dibi; mum kapanmadan aralık yoktur.
5. **Kapanışı bekle.** Mumun aralığın dışına taşması sinyal değildir; dışarıda kapanması sinyaldir. Giriş
   bir sonraki dakikada.
6. **Stop karşı uçta, emir girişle birlikte.** Stopun uzaklığı riskin kendisidir; pozisyon büyüklüğü bu
   uzaklıktan kurulur (1R = hesap riskinin sabit bir payı).
7. **Gün sonunda kapat.** 16:55 New York: TSİ 23:55 (ABD yaz saati) ya da 00:55.
8. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
