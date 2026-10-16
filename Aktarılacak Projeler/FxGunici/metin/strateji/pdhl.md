### Ne

Önceki FX işlem gününün tepesi (*previous day high*, PDH) ve dibi (*previous day low*, PDL) bugünün en çok
izlenen iki seviyesidir. Kural, fiyat bu seviyelerden birini kapanışla **kestiğinde** kesiş yönünde işleme girer:
dünün tepesinin üstünde kapanış alış, dünün dibinin altında kapanış satış.

### Piyasa mantığı

Dünün uçları, dün o seviyelerde dönen piyasanın bugün yeniden sınayacağı yerlerdir; çoğu masanın stop'u ve
kırılım emri de oradadır. Kırılım savunusu: dünün aralığından çıkan fiyat, dünün dengesini terk etmiştir ve
emirler tetiklendikçe hareket hızlanır. Karşı savunu fade dersinin "sahte önceki gün tepe/dip" kuralıdır: aynı
seviyenin aşılıp geri dönülmesi stop toplamanın ta kendisidir. İkisi aynı seviyeyle sınanıyor; hangisinin daha sık
olduğu ölçünün kendisidir.

### Kurallar

- **Seviyeler.** Önceki FX işlem gününün (17:00 → 17:00 New York) orta fiyattan tepesi ve dibi.
- **Pencere.** Gün başından (17:00 New York) ya da Londra 08:00'den 14:00 New York'a kadar kapanan mumlar.
- **Sinyal.** Seviyeyi **kesen** ilk kapanış: bir önceki mum seviyenin içinde kapanmış, bu mum dışında kapanmış.
  Fiyat pencere açılmadan seviyenin dışındaysa önce içeri girmesi, sonra yeniden kesmesi gerekir. Gün başına tek
  işlem.
- **Stop.** Sinyal mumunun karşı ucu ya da seviyenin {{= "0,5" }} × ATR(14) içi (alışta tepenin altında, satışta dibin
  üstünde).

{{! kural }}

Varsayılan pencereyi Londra açılışında başlatır, stop'u sinyal mumunun karşı ucuna koyar ve 2R hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.baslangic == "londra" and B.varsayilan.stop_kurali == "sinyal_mumu" and B.varsayilan.hedef == "2R" and B.varsayilan.stop_turu == "sert" }}
Gece seansının kırılımları bu yüzden dışarıda kalır: Asya'da kesilen bir seviye Londra açılışında yeniden
kesilmedikçe sinyal üretmez.

### Örnekler

{{! sekil ornek "Örnek günler — PDH/PDL" }}

{{! ornek }}

Figürde mavi çizgiler dünün tepesi ve dibidir. Sinyal mumunun boyu riski belirler: seviyeyi uzun bir mumla kesen
kırılımın stop'u da uzaktır.

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

{{! kosullar }}

Dünün aralığının ATR'ye oranı (önceki gün aralığı / ATR) bu kural için ayrıca okunmalı: dar bir dünün uçları bugüne
yakındır ve kolay kesilir.

### Kontrol listesi

1. **Seviyeleri işaretle.** 17:00 New York'ta kapanan günün tepesi ve dibi (TSİ yazın 00:00, kışın 01:00).
2. **Pencere.** Londra 08:00 (TSİ 10:00 ya da 11:00) → 14:00 New York (TSİ 21:00 ya da 22:00).
3. **Kesişi bekle.** Önceki kapanış içeride, bu kapanış dışarıda; giriş sonraki dakikada.
4. **Stop sinyal mumunun karşı ucunda, hedef 2R.**
5. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
